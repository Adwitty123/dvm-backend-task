from django.urls import path
from . import views

app_name = 'music'
urlpatterns = [
    path('', views.charts, name='charts'),
    path('search/', views.search, name='search'),
    path('passport/', views.passport, name='passport'),
]
