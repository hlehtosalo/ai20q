import re
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.db import transaction
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from .models import Conversation, TargetWord, PlayerStats
from openai import OpenAI

max_questions = 20
question_system_message = 'You are the answerer in the game "twenty questions". The word to guess is _. You are asked a yes or no question about _. If the answers yes and no are roughly equally good, say "Maybe".'

common_prelude = 'We are playing the game "twenty questions" and you are trying to guess the word. The word can be any single-word common noun (not a name).'
hint_prelude = ' Ask a yes or no question that is designed to eliminate half the possibilities. The question must be less than 99 characters long.'
guess_prelude = ' You have only one chance, so try to guess the word even if you are not sure. Say only the word and nothing else.'
common_intro = ' Use any relevant information gathered so far by the following questions and answers:'

class Bar:
    number = 0
    length = ""
    def __init__(self, number, length):
        self.number = number
        self.length = length

@login_required
def index(request, hint = ""):
    try:
        conversation = Conversation.objects.get(name = request.user.username)
    except Conversation.DoesNotExist:
        conversation = Conversation()
    try:
        stats = PlayerStats.objects.get(name = request.user.username)
    except PlayerStats.DoesNotExist:
        stats = PlayerStats()

    played_count = stats.played_count
    if conversation.length > 0 and not conversation.solved:
        played_count -= 1
    solved_counts = list(stats.get_solved_counts())
    solved_count_max = float(max(max(solved_counts), 1))
    bars = []
    for solved_count in solved_counts:
        percentage = float(solved_count) * 100 / solved_count_max
        bars.append(Bar(solved_count, str(percentage) + "%"))
    
    context = {
        "messages": conversation.get_messages(),
        "questions_asked": conversation.length,
        "questions_left": max_questions - conversation.length,
        "hints_left": conversation.hints_left,
        "is_solved": conversation.solved,
        "target_word": conversation.target_word,
        "username": request.user.username,
        "user_initial": request.user.username[0].upper(),
        "played_count": played_count,
        "win_rate": int(float(played_count - stats.failed_count) * 100 / float(max(played_count, 1))),
        "current_streak": stats.current_streak,
        "max_streak": stats.max_streak,
        "solved_bars": bars,
        "hint": hint
        }
    return render(request, "alphatest/index.html", context)

def clean_question(question):
    question = (question[:1].upper() + question[1:]).replace("_", " ")
    if question[len(question) - 1] == "?":
        return question
    else:
        return question + "?"

def is_filler_word(word):
    if len(word) < 3:
        return True
    return word == "the" or word == "its" or word == "it's"

def is_correct(question, target_word):
    result = False
    for word in re.split("[\s,\.\?!]", question):
        word = word.lower()
        if not is_filler_word(word):
            if word.strip("'\"") == target_word:
                result = True
            else:
                return False
    return result

def pack_QA(question, answer):
    if answer == "yes":
        return question[: len(question) - 1] + "Y_"
    elif answer == "no":
        return question[: len(question) - 1] + "N_"
    elif answer == "maybe":
        return question[: len(question) - 1] + "M_"
    elif answer == "!":
        return question[: len(question) - 1] + "C_"
    else:
        return question[: len(question) - 1] + "X_"

def get_answer(question, target_word):
    client = OpenAI()
    completion = client.chat.completions.create(
        model = "gpt-3.5-turbo-0125",
        messages = [
            { "role": "system", "content": question_system_message.replace("_", target_word) },
            { "role": "user", "content": question }
            ],
        temperature = 0,
        max_tokens = 1
        )
    return completion.choices[0].message.content.lower()

def first_alpha_index(s):
    for i in range(len(s)):
        if s[i].isalpha():
            return i
    return len(s)

def first_after_questionmark_index(s):
    for i in range(len(s)):
        if s[i] == "?":
            return i + 1
    return len(s)

def clean_hint(hint):
    return hint[first_alpha_index(hint):first_after_questionmark_index(hint)]

def get_hint_temperature(conversation_length):
    return 2.0 * pow(0.9, conversation_length)

def get_hint(conversation):
    msgs = [ common_prelude ]
    if conversation.length >= max_questions - 2:
        msgs.append(guess_prelude)
    else:
        msgs.append(hint_prelude)
    if conversation.length > 0:
        msgs.append(common_intro)
        for message in conversation.get_messages():
            msgs.append("\n" + message.question)
            msgs.append(" " + message.answer)
    client = OpenAI()
    completion = client.chat.completions.create(
        model = "gpt-4",
        messages = [ { "role": "user", "content": "".join(msgs) } ],
        temperature = get_hint_temperature(conversation.length)
        )
    return clean_hint(completion.choices[0].message.content)

def log_error():
    pass #TODO

@login_required
def ask(request):
    question = request.POST["question"]
    if question == "" or len(question) > 98:
        return HttpResponseRedirect(reverse("alphatest:index"))
    
    try:
        conversation = Conversation.objects.get(name = request.user.username)
    except Conversation.DoesNotExist:
        conversation = Conversation(name = request.user.username, target_word = TargetWord.objects.get(pk = 1).text)
    
    if conversation.solved or conversation.length >= max_questions:
        return HttpResponseRedirect(reverse("alphatest:index"))
    
    if question == "HINT":
        try:
            stats = PlayerStats.objects.get(name = request.user.username)
        except PlayerStats.DoesNotExist:
            stats = PlayerStats(name = request.user.username)
        stats.hints_used += 1
        stats.save()
        return HttpResponseRedirect(reverse("alphatest:index", kwargs = {"hint": get_hint(conversation)}))
    
    question = clean_question(question)
    answer = ""
    if is_correct(question, conversation.target_word):
        answer = "!"
        conversation.solved = True
    else:
        answer = get_answer(question, conversation.target_word)
    
    conversation.length += 1
    conversation.text += pack_QA(question, answer)
    conversation.update_time = timezone.now()
    conversation.save()
    
    if conversation.length == 1 and not conversation.solved:
        try:
            stats = PlayerStats.objects.get(name = request.user.username)
        except PlayerStats.DoesNotExist:
            stats = PlayerStats(name = request.user.username)
        stats.played_count += 1
        stats.save()
        
        try:
            with transaction.atomic():
                target_word = TargetWord.objects.get(pk = conversation.target_word_index + 1)
                target_word.played_count += 1
                target_word.save()
        except:
            log_error()
    
    if conversation.solved or conversation.length == max_questions:
        try:
            stats = PlayerStats.objects.get(name = request.user.username)
        except PlayerStats.DoesNotExist:
            stats = PlayerStats(name = request.user.username)
        if conversation.length == 1:
            stats.played_count += 1
        if conversation.solved:
            solved_counts = list(stats.get_solved_counts())
            solved_counts[conversation.length - 1] += 1
            stats.set_solved_counts(solved_counts)
            stats.current_streak += 1
            if stats.current_streak > stats.max_streak:
                stats.max_streak = stats.current_streak
        else:
            stats.failed_count += 1
            stats.current_streak = 0
        stats.save()
        
        try:
            with transaction.atomic():
                target_word = TargetWord.objects.get(pk = conversation.target_word_index + 1)
                if conversation.length == 1:
                    target_word.played_count += 1
                if conversation.solved:
                    solved_counts = list(target_word.get_solved_counts())
                    solved_counts[conversation.length - 1] += 1
                    target_word.set_solved_counts(solved_counts)
                else:
                    target_word.failed_count += 1
                target_word.save()
        except:
            log_error()
    
    return HttpResponseRedirect(reverse("alphatest:index"))

@login_required
def next_word(request):
    try:
        conversation = Conversation.objects.get(name = request.user.username)
        conversation.target_word_index += 1;
        if conversation.target_word_index >= TargetWord.objects.count():
            conversation.target_word_index = 0
        conversation.text = ""
        conversation.length = 0
        conversation.hints_left = 3
        conversation.solved = False
    except Conversation.DoesNotExist:
        conversation = Conversation(name = request.user.username)
    conversation.target_word = TargetWord.objects.get(pk = conversation.target_word_index + 1).text
    conversation.update_time = timezone.now()
    conversation.save()
    return HttpResponseRedirect(reverse("alphatest:index"))

@login_required
def request_hint(request):
    try:
        conversation = Conversation.objects.get(name = request.user.username)
    except Conversation.DoesNotExist:
        conversation = Conversation(name = request.user.username, target_word = TargetWord.objects.get(pk = 1).text)
    
    if conversation.solved or conversation.length >= max_questions or conversation.hints_left <= 0:
        return HttpResponseRedirect(reverse("alphatest:index"))
    
    hint = get_hint(conversation)
    conversation.hints_left -= 1
    conversation.save()
    
    try:
        stats = PlayerStats.objects.get(name = request.user.username)
    except PlayerStats.DoesNotExist:
        stats = PlayerStats(name = request.user.username)
    stats.hints_used += 1
    stats.save()
    return HttpResponseRedirect(reverse("alphatest:index", kwargs = {"hint": hint}))
