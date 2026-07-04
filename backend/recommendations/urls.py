from django.urls import path

from .views import ChatView, HomePersonalizedRecommendationsView, PersonalizedRecommendationsView


urlpatterns = [
    path("personalized/", PersonalizedRecommendationsView.as_view()),
    path("personalized/home/", HomePersonalizedRecommendationsView.as_view()),
    path("chat/", ChatView.as_view()),
]

