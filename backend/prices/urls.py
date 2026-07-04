from django.urls import path

from .views import BestDealsView, EpicFreeGamesView, PopularDealsView


urlpatterns = [
    path("deals/popular/", PopularDealsView.as_view()),
    path("deals/best/", BestDealsView.as_view()),
    path("epic/free-games/", EpicFreeGamesView.as_view()),
]

