from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.sentiment_view, name='sentiment_dashboard'),
    path('news/latest/', views.latest_news, name='latest_news'),
    path('news/feed/', views.news_feed, name='news_feed'),
    path('stats/', views.statistics_view, name='statistics'),
]
