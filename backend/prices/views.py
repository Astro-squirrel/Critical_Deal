from rest_framework.views import APIView
from django.db.models import F, FloatField, Value
from django.db.models.functions import Cast, Ln

from common.responses import fail, ok
from external_apis.services import ItadApiError
from games.serializers import GameCardSerializer
from games.services import game_queryset
from .models import EpicFreeGame
from .serializers import EpicFreeGameSerializer
from .services import is_free_games_cache_stale, is_steam_price_cache_stale, sync_daily_deals, sync_epic_free_games


class PopularDealsView(APIView):
    def get(self, request):
        sync_error = None
        if request.query_params.get("refresh") == "1" or is_steam_price_cache_stale():
            try:
                sync_daily_deals(deals_limit=200, popular_limit=100, include_free_games=False)
            except ItadApiError as exc:
                sync_error = exc
        games = _local_popular_games()
        if not games:
            try:
                sync_daily_deals(deals_limit=24, popular_limit=50, include_free_games=False)
            except ItadApiError as exc:
                sync_error = exc
            games = _local_popular_games()
        if not games and sync_error:
            return fail(str(sync_error), status=502)
        return ok(GameCardSerializer(_unique_games(games), many=True).data)


class BestDealsView(APIView):
    def get(self, request):
        sync_error = None
        if request.query_params.get("refresh") == "1" or is_steam_price_cache_stale():
            try:
                sync_daily_deals(deals_limit=200, popular_limit=100, include_free_games=False)
            except ItadApiError as exc:
                sync_error = exc
        games = list(
            game_queryset(include_related_products=False)
            .filter(prices__store__name__iexact="Steam", prices__current_price__gt=0, prices__discount_rate__gte=10)
            .distinct()
            .order_by("-max_discount", "best_price")[:8]
        )
        if not games:
            try:
                sync_daily_deals(deals_limit=24, popular_limit=0, include_free_games=False)
            except ItadApiError as exc:
                sync_error = exc
            games = list(
                game_queryset(include_related_products=False)
                .filter(prices__store__name__iexact="Steam", prices__current_price__gt=0, prices__discount_rate__gte=10)
                .distinct()
                .order_by("-max_discount", "best_price")[:8]
            )
        if not games:
            games = _local_popular_games()
        if not games and sync_error:
            return fail(str(sync_error), status=502)
        return ok(GameCardSerializer(_unique_games(games), many=True).data)


class EpicFreeGamesView(APIView):
    def get(self, request):
        games = EpicFreeGame.objects.order_by("ends_at", "title")
        if request.query_params.get("refresh") == "1" or is_free_games_cache_stale():
            try:
                games = sync_epic_free_games()
            except ItadApiError as exc:
                if request.query_params.get("refresh") == "1" and not games.exists():
                    return fail(str(exc), status=502)
        return ok(EpicFreeGameSerializer(games, many=True).data)


def _local_popular_games(limit=8):
    discounted = list(
        game_queryset(include_related_products=False)
        .filter(prices__store__name__iexact="Steam", prices__current_price__gt=0, prices__discount_rate__gt=0)
        .filter(steam_review_count__gte=1000, steam_review_score__gte=70)
        .annotate(
            deal_rank_score=(
                Ln(Cast(F("steam_review_count"), FloatField()) + Value(1.0)) * Value(8.0)
                + Cast(F("steam_review_score"), FloatField()) * Value(0.7)
                + Cast(F("max_discount"), FloatField()) * Value(1.2)
            )
        )
        .distinct()
        .order_by("-deal_rank_score", "-max_discount", "-steam_review_count")[: limit * 3]
    )
    if discounted:
        return _unique_games(discounted, limit=limit)

    priced = list(
        game_queryset(include_related_products=False)
        .filter(prices__store__name__iexact="Steam", prices__current_price__gt=0)
        .distinct()
        .order_by("-steam_review_count", "best_price")[: limit * 3]
    )
    if priced:
        return _unique_games(priced, limit=limit)

    return _unique_games(
        list(game_queryset(include_related_products=False).order_by("-steam_review_count", "title")[: limit * 3]),
        limit=limit,
    )


def _unique_games(games, limit=None):
    unique = []
    seen = set()
    for game in games:
        if game.id in seen:
            continue
        seen.add(game.id)
        unique.append(game)
        if limit and len(unique) >= limit:
            break
    return unique
