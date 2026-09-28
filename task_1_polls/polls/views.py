from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db import IntegrityError, transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import generic
from django.views.decorators.http import require_POST
from .forms import PollForm
from .models import Choice, Question, Vote


class IndexView(generic.ListView):
    template_name = 'polls/index.html'
    context_object_name = 'questions'
    paginate_by = 10

    def get_queryset(self):
        return Question.objects.filter(pub_date__lte=timezone.now()).select_related('author')


class DetailView(generic.DetailView):
    model = Question
    template_name = 'polls/detail.html'

    def get_queryset(self):
        return Question.objects.filter(pub_date__lte=timezone.now()).prefetch_related('choice_set')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['has_voted'] = self.request.user.is_authenticated and Vote.objects.filter(user=self.request.user, question=self.object).exists()
        return context


class ResultsView(DetailView):
    template_name = 'polls/results.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        choices = list(self.object.choice_set.all())
        total = sum(choice.votes for choice in choices)
        context['total'] = total
        context['rows'] = [{'choice': choice, 'percentage': round(choice.votes * 100 / total, 1) if total else 0} for choice in choices]
        return context


@login_required
@require_POST
def vote(request, pk):
    question = get_object_or_404(Question, pk=pk, pub_date__lte=timezone.now())
    if not question.is_open:
        messages.error(request, 'This poll is closed.')
        return redirect('polls:results', pk=pk)
    try:
        choice = question.choice_set.get(pk=request.POST.get('choice'))
    except (Choice.DoesNotExist, ValueError, TypeError):
        return render(request, 'polls/detail.html', {'question': question, 'error_message': 'Select a valid choice.'}, status=400)
    try:
        with transaction.atomic():
            Vote.objects.create(user=request.user, question=question, choice=choice)
            Choice.objects.filter(pk=choice.pk).update(votes=F('votes') + 1)
    except IntegrityError:
        messages.info(request, 'You have already voted in this poll.')
    return redirect('polls:results', pk=pk)


@login_required
def create(request):
    form = PollForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        question = form.save(request.user)
        messages.success(request, 'Your poll is live. Share its URL to invite votes.')
        return redirect('polls:detail', pk=question.pk)
    return render(request, 'polls/create.html', {'form': form})


def signup(request):
    form = UserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('polls:index')
    return render(request, 'registration/signup.html', {'form': form})
