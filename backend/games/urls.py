from django.urls import path

from .views import (
    GameAIAnalysisView,
    GameCommentDetailView,
    GameCommentReactionView,
    GameCommentView,
    GameDetailView,
    GameHistoryView,
    GameListView,
    GameOtherStorePricesView,
    GamePricesView,
    GameRecommendationView,
    GameRelatedProductsView,
    GameSearchView,
    GenreListView,
    UserCommentListView,
)


urlpatterns = [
    path("search/", GameSearchView.as_view()),
    path("genres/", GenreListView.as_view()),
    path("comments/users/<int:user_id>/", UserCommentListView.as_view()),
    path("", GameListView.as_view()),
    path("<int:pk>/", GameDetailView.as_view()),
    path("<int:pk>/comments/", GameCommentView.as_view()),
    path("<int:pk>/comments/<int:comment_pk>/", GameCommentDetailView.as_view()),
    path("<int:pk>/comments/<int:comment_pk>/reaction/", GameCommentReactionView.as_view()),
    path("<int:pk>/prices/", GamePricesView.as_view()),
    path("<int:pk>/other-prices/", GameOtherStorePricesView.as_view()),
    path("<int:pk>/related-products/", GameRelatedProductsView.as_view()),
    path("<int:pk>/history/", GameHistoryView.as_view()),
    path("<int:pk>/recommendation/", GameRecommendationView.as_view()),
    path("<int:pk>/ai-analysis/", GameAIAnalysisView.as_view()),
]

