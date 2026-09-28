from datetime import timedelta
from django.conf import settings
from django.contrib import admin
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Question(models.Model):
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published', default=timezone.now)
    closes_at = models.DateTimeField(null=True, blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-pub_date', '-pk']
        constraints = [models.CheckConstraint(condition=Q(closes_at__isnull=True) | Q(closes_at__gt=models.F('pub_date')), name='closing_after_publication')]

    def __str__(self):
        return self.question_text

    @admin.display(boolean=True, ordering='pub_date', description='Published recently?')
    def was_published_recently(self):
        now = timezone.now()
        return now - timedelta(days=1) <= self.pub_date <= now

    @property
    def is_open(self):
        now = timezone.now()
        return self.pub_date <= now and (self.closes_at is None or self.closes_at > now)


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice_text = models.CharField(max_length=200)
    votes = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.choice_text


class Vote(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'question'], name='one_vote_per_user_question')]
