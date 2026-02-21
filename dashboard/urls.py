from django.urls import path
from .views import sentiment_view
from . import views

urlpatterns = [
    path('', sentiment_view, name='sentiment_dashboard'),
    path("news/latest/", views.latest_news, name="latest_news"),
    path("news/feed/", views.news_feed, name="news_feed"),   
    path("stats/", views.statistics_view, name="statistics"),

]
