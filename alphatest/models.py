import datetime
from django.db import models
from django.contrib import admin

class Message:
    question = ""
    answer = ""
    class_name = ""

def string_to_message(s):
    lastChar = s[len(s) - 1]
    result = Message()
    result.question = s[: len(s) - 1] + '?'
    
    if lastChar == "Y":
        result.answer = "Yes."
        result.class_name = "yes"
    elif lastChar == "N":
        result.answer = "No."
        result.class_name = "no"
    elif lastChar == "M":
        result.answer = "Maybe."
        result.class_name = "maybe"
    elif lastChar == "X":
        result.answer = "Can't say."
        result.class_name = "dunno"
    elif lastChar == "C":
        result.answer = "Correct!"
        result.class_name = "correct"
    else:
        return Message()
    
    return result

class Conversation(models.Model):
    name = models.CharField(max_length = 20)
    target_word = models.CharField(max_length = 20, default = "")
    target_word_index = models.IntegerField(default = 0)
    text = models.CharField(max_length = 2000, default = "")
    length = models.IntegerField(default = 0)
    hints_left = models.IntegerField(default = 3)
    solved = models.BooleanField(default = False)
    update_time = models.DateTimeField("last updated")
    def __str__(self):
        return self.name
    def get_messages(self):
        return map(string_to_message, filter(None, self.text.split("_")))

class TargetWord(models.Model):
    text = models.CharField(max_length = 20, unique = True)
    played_count = models.IntegerField(default = 0)
    solved_counts = models.CharField(max_length = 160, default = "0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
    failed_count = models.IntegerField(default = 0)
    def __str__(self):
        return self.text
    def get_solved_counts(self):
        return map(int, self.solved_counts.split(","))
    def set_solved_counts(self, counts):
        self.solved_counts = ",".join(map(str, counts))

class PlayerStats(models.Model):
    name = models.CharField(max_length = 20)
    played_count = models.IntegerField(default = 0)
    solved_counts = models.CharField(max_length = 80, default = "0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
    failed_count = models.IntegerField(default = 0)
    current_streak = models.IntegerField(default = 0)
    max_streak = models.IntegerField(default = 0)
    hints_used = models.IntegerField(default = 0)
    def __str__(self):
        return self.name
    def get_solved_counts(self):
        return map(int, self.solved_counts.split(","))
    def set_solved_counts(self, counts):
        self.solved_counts = ",".join(map(str, counts))
    class Meta:
        verbose_name_plural = "player stats"
