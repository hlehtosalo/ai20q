from django.core.management.base import BaseCommand
from alphatest.models import TargetWord

def clean(word):
    return word.strip().lower()

def long_enough(word):
    return len(word) > 2

def short_enough(word):
    return len(word) < 21

def legal_characters(word):
    return word.isalpha()

class Command(BaseCommand):
    help = "Adds the contents of the given file to the target word database"

    def add_arguments(self, parser):
        parser.add_argument("filename")

    def handle(self, *args, **options):
        filename = options["filename"]
        self.stdout.write("Adding words from file " + filename)
        file = open(filename, "r")
        data = file.read()
        file.close()
        
        words = list(map(clean, data.split("\n")))
        
        word_count = len(words)
        self.stdout.write(str(word_count) + " words encountered.")
        
        words = list(filter(long_enough, words))
        self.stdout.write(str(word_count - len(words)) + " short words skipped.")
        word_count = len(words)
        
        words = list(filter(short_enough, words))
        self.stdout.write(str(word_count - len(words)) + " long words skipped.")
        word_count = len(words)
        
        words = list(filter(legal_characters, words))
        self.stdout.write(str(word_count - len(words)) + " words with illegal characters skipped.")
        word_count = len(words)
        
        words = list(dict.fromkeys(words))
        self.stdout.write(str(word_count - len(words)) + " duplicate words skipped.")
        word_count = len(words)
        
        self.stdout.write("Adding " + str(word_count) + " words to database.")
        for word in words:
            entry = TargetWord(text = word)
            try:
                entry.save()
            except django.db.IntegrityError:
                self.stdout.write("Word " + word + " already in database, skipped.")
        
        self.stdout.write("Done!")
