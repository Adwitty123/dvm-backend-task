from django.contrib.auth import views as auth_views
from django.urls import include, path
from . import views

poll_patterns = ([
    path('', views.IndexView.as_view(), name='index'),
    path('polls/create/', views.create, name='create'),
    path('polls/<int:pk>/', views.DetailView.as_view(), name='detail'),
    path('polls/<int:pk>/results/', views.ResultsView.as_view(), name='results'),
    path('polls/<int:pk>/vote/', views.vote, name='vote'),
], 'polls')
urlpatterns = [
    path('', include(poll_patterns)),
    path('accounts/signup/', views.signup, name='signup'),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
]
