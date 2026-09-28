from django.core.management.base import BaseCommand
from polls.models import Choice, Question


class Command(BaseCommand):
    help = 'Create two sample polls without creating user accounts.'

    def handle(self, *args, **options):
        for title, choices in [
            ('Which backend topic should we explore next?', ['Databases', 'APIs', 'Testing']),
            ('What powers your late-night coding?', ['Coffee', 'Tea', 'Music', 'Sleep']),
        ]:
            question, created = Question.objects.get_or_create(question_text=title)
            if created:
                Choice.objects.bulk_create([Choice(question=question, choice_text=value) for value in choices])
        self.stdout.write(self.style.SUCCESS('Sample polls are ready.'))
