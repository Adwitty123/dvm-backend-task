from datetime import timedelta
from django import forms
from django.db import transaction
from django.utils import timezone
from .models import Choice, Question


class PollForm(forms.Form):
    question = forms.CharField(max_length=200)
    choices = forms.CharField(widget=forms.Textarea(attrs={'rows': 6}), help_text='Enter 2–8 choices, one per line. Each choice may contain up to 200 characters.')
    duration = forms.TypedChoiceField(coerce=int, choices=[(1, '1 day'), (3, '3 days'), (7, '7 days'), (30, '30 days')], initial=7)

    def clean_choices(self):
        choices = [line.strip() for line in self.cleaned_data['choices'].splitlines() if line.strip()]
        if not 2 <= len(choices) <= 8:
            raise forms.ValidationError('Provide between 2 and 8 choices.')
        if any(len(choice) > 200 for choice in choices):
            raise forms.ValidationError('Each choice must contain at most 200 characters.')
        if len({choice.casefold() for choice in choices}) != len(choices):
            raise forms.ValidationError('Choices must be unique, ignoring letter case.')
        return choices

    @transaction.atomic
    def save(self, author):
        now = timezone.now()
        question = Question.objects.create(question_text=self.cleaned_data['question'], author=author, pub_date=now, closes_at=now + timedelta(days=self.cleaned_data['duration']))
        Choice.objects.bulk_create([Choice(question=question, choice_text=text) for text in self.cleaned_data['choices']])
        return question
