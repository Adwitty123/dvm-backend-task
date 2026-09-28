from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from .forms import PollForm
from .models import Choice, Question, Vote


class QuestionTests(TestCase):
    def test_recent_publication_boundaries(self):
        for offset, expected in [(30, False), (-2, False), (-0.5, True)]:
            with self.subTest(offset=offset):
                question = Question(pub_date=timezone.now() + timedelta(days=offset))
                self.assertEqual(question.was_published_recently(), expected)

    def test_empty_index(self):
        self.assertContains(self.client.get('/'), 'No polls are available')

    def test_future_questions_hidden_everywhere(self):
        question = Question.objects.create(question_text='Tomorrow', pub_date=timezone.now() + timedelta(days=1))
        self.assertNotContains(self.client.get('/'), 'Tomorrow')
        for name in ['detail', 'results']:
            self.assertEqual(self.client.get(reverse(f'polls:{name}', args=[question.pk])).status_code, 404)

    def test_past_questions_are_visible(self):
        question = Question.objects.create(question_text='Visible')
        self.assertContains(self.client.get('/'), question.question_text)
        self.assertContains(self.client.get(reverse('polls:detail', args=[question.pk])), question.question_text)

    def test_pagination(self):
        for number in range(11):
            Question.objects.create(question_text=f'Question {number}')
        self.assertEqual(len(self.client.get('/').context['questions']), 10)
        self.assertEqual(len(self.client.get('/?page=2').context['questions']), 1)


class CommunityTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('listener', password='A-long-password-42')
        self.question = Question.objects.create(question_text='Coffee or tea?')
        self.choice = Choice.objects.create(question=self.question, choice_text='Tea')
        self.url = reverse('polls:vote', args=[self.question.pk])

    def test_anonymous_cannot_vote_or_create(self):
        self.assertEqual(self.client.post(self.url, {'choice': self.choice.pk}).status_code, 302)
        self.assertEqual(self.client.get(reverse('polls:create')).status_code, 302)
        self.assertEqual(Vote.objects.count(), 0)

    def test_vote_once_even_if_post_is_replayed(self):
        self.client.force_login(self.user)
        for _ in range(2):
            self.assertRedirects(self.client.post(self.url, {'choice': self.choice.pk}), reverse('polls:results', args=[self.question.pk]))
        self.choice.refresh_from_db()
        self.assertEqual(self.choice.votes, 1)
        self.assertEqual(Vote.objects.count(), 1)

    def test_get_cannot_vote(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_csrf_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(self.url, {'choice': self.choice.pk}).status_code, 403)

    def test_missing_invalid_and_foreign_choices(self):
        other = Question.objects.create(question_text='Other')
        foreign = Choice.objects.create(question=other, choice_text='No')
        self.client.force_login(self.user)
        for value in ['', 'invalid', str(foreign.pk)]:
            with self.subTest(value=value):
                self.assertEqual(self.client.post(self.url, {'choice': value}).status_code, 400)
        self.assertEqual(Vote.objects.count(), 0)

    def test_closed_poll_cannot_receive_votes(self):
        self.question.pub_date = timezone.now() - timedelta(days=2)
        self.question.closes_at = timezone.now() - timedelta(days=1)
        self.question.save()
        self.client.force_login(self.user)
        self.client.post(self.url, {'choice': self.choice.pk})
        self.assertEqual(Vote.objects.count(), 0)

    def test_database_rejects_duplicate_vote(self):
        Vote.objects.create(user=self.user, question=self.question, choice=self.choice)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Vote.objects.create(user=self.user, question=self.question, choice=self.choice)

    def test_create_poll_and_choices(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('polls:create'), {'question': 'Best editor?', 'choices': 'Vim\nVS Code', 'duration': 3})
        self.assertEqual(response.status_code, 302)
        question = Question.objects.get(question_text='Best editor?')
        self.assertEqual(question.author, self.user)
        self.assertEqual(question.choice_set.count(), 2)
        self.assertTrue(question.is_open)
        self.assertAlmostEqual((question.closes_at - question.pub_date).total_seconds(), 3 * 86400)

    def test_bad_poll_choices(self):
        for choices in ['One', 'Tea\ntea', '\n'.join(str(i) for i in range(9)), 'A' * 201 + '\nB']:
            with self.subTest(choices=choices):
                self.assertFalse(PollForm({'question': 'Test', 'choices': choices, 'duration': 7}).is_valid())

    def test_results_without_votes(self):
        response = self.client.get(reverse('polls:results', args=[self.question.pk]))
        self.assertEqual(response.context['total'], 0)
        self.assertEqual(response.context['rows'][0]['percentage'], 0)

    def test_signup_logs_in_new_user(self):
        response = self.client.post(reverse('signup'), {'username': 'newuser', 'password1': 'Unique-long-phrase-982!', 'password2': 'Unique-long-phrase-982!'})
        self.assertRedirects(response, '/')
        self.assertIn('_auth_user_id', self.client.session)
