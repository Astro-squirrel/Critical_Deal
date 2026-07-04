from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.paginator import EmptyPage, Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView

from common.responses import fail, ok
from accounts.models import UserGame
from accounts.utils import user_avatar_url
from external_apis.services import ItadApiError, itad_service
from prices.services import sync_history_for_game, sync_prices_for_game
from recommendations.serializers import GameAIAnalysisSerializer
from recommendations.services import analyze_purchase, get_or_create_ai_analysis, get_or_create_personalized_ai_analysis
from .models import Game, GameComment, GameCommentReaction, Genre, RelatedProduct
from .serializers import GameCardSerializer, GameCommentCreateSerializer, GameCommentSerializer, GameDetailSerializer, PriceHistorySerializer
from .services import (
    ensure_game_image_data,
    game_queryset,
    game_search_filter,
    local_game_suggestions,
    search_games,
    sync_player_history_for_game,
    sync_related_products_for_game,
)


class GamePagination(PageNumberPagination):
    page_size = 40
    page_size_query_param = "page_size"
    max_page_size = 80


class GameSearchView(APIView):
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        include_dlc = request.query_params.get("include_dlc") in {"1", "true", "True"}
        if request.query_params.get("suggest") == "1":
            queryset = local_game_suggestions(query, include_dlc=include_dlc) if query else game_queryset(include_related_products=False)
            games = list(queryset[:8])
            ensure_game_image_data(games, limit=8)
            return ok(GameCardSerializer(games, many=True).data)
        try:
            queryset = search_games(query, include_dlc=include_dlc) if query else game_queryset(include_related_products=False)
        except ItadApiError as exc:
            return fail(str(exc), status=502)
        games = list(queryset[:20])
        ensure_game_image_data(games, limit=12)
        return ok(GameCardSerializer(games, many=True).data)


class GenreListView(APIView):
    def get(self, request):
        genres = (
            Genre.objects.annotate(
                game_count=Count(
                    "game",
                    filter=Q(
                        game__prices__store__name__iexact="Steam",
                        game__prices__current_price__gte=0,
                        game__related_product_entries__isnull=True,
                    ),
                    distinct=True,
                )
            )
            .filter(game_count__gt=0)
            .order_by("-game_count", "name")
            .values_list("name", flat=True)
        )
        return ok(list(genres))


class GameListView(APIView):
    def get(self, request):
        include_dlc = request.query_params.get("include_dlc") in {"1", "true", "True"}
        include_bundle = request.query_params.get("include_bundle") in {"1", "true", "True"}
        include_related_products = include_dlc or include_bundle
        queryset = (
            game_queryset(include_related_products=include_related_products)
            .filter(prices__store__name__iexact="Steam", prices__current_price__gte=0)
            .distinct()
        )
        if include_related_products:
            related_filter = Q(related_product_entries__isnull=True)
            if include_dlc:
                related_filter |= Q(related_product_entries__product_type=RelatedProduct.DLC)
            if include_bundle:
                related_filter |= Q(related_product_entries__product_type=RelatedProduct.BUNDLE)
            queryset = queryset.filter(related_filter)
        query = request.query_params.get("q", "").strip()
        genres = request.query_params.getlist("genre") or request.query_params.getlist("genre[]")
        min_discount = request.query_params.get("discount")
        discounted_only = request.query_params.get("discounted") in {"1", "true", "True"}
        min_price = request.query_params.get("min_price")
        max_price = request.query_params.get("max_price")
        min_review_score = request.query_params.get("review_score")
        min_review_count = request.query_params.get("review_count")
        ordering = request.query_params.get("ordering", "-steam_review_count")
        if ordering == "-popularity_score":
            ordering = "-steam_review_count"
        if genres:
            queryset = queryset.filter(genres__name__in=genres)
        if query:
            queryset = queryset.filter(game_search_filter(query))
        if discounted_only:
            queryset = queryset.filter(prices__discount_rate__gt=0)
        if min_discount:
            queryset = queryset.filter(prices__discount_rate__gte=min_discount)
        if min_price:
            queryset = queryset.filter(prices__current_price__gte=min_price)
        if max_price:
            queryset = queryset.filter(prices__current_price__lte=max_price)
        if min_review_score:
            queryset = queryset.filter(steam_review_score__gte=min_review_score, steam_review_count__gt=0)
        if min_review_count:
            queryset = queryset.filter(steam_review_count__gte=min_review_count)
        if ordering in ["title", "-steam_review_count", "best_price", "-max_discount"]:
            queryset = queryset.order_by(ordering)
        paginator = GamePagination()
        page = paginator.paginate_queryset(queryset.distinct(), request)
        data = GameCardSerializer(page, many=True).data
        return paginator.get_paginated_response({"success": True, "message": "ok", "data": data})


class GameDetailView(APIView):
    def get(self, request, pk):
        game = game_queryset().get(pk=pk)
        if request.query_params.get("refresh") == "1":
            try:
                sync_prices_for_game(game, force=True, history_days=730)
            except ItadApiError as exc:
                return fail(str(exc), status=502)
        ensure_game_image_data([game], limit=1)
        sync_player_history_for_game(game, days=14, force=request.query_params.get("refresh") == "1")
        return ok(GameDetailSerializer(game, context={"include_other_store_prices": False}).data)


class GameCommentView(APIView):
    def get(self, request, pk):
        game = get_object_or_404(Game, pk=pk)
        comment_page = _paginated_comments(game, request)
        visible_comments = comment_page["top_comments"] + comment_page["comments"]
        context = _comment_context(game, visible_comments, request)
        return ok(
            {
                "total_count": comment_page["total_count"],
                "top_comments": GameCommentSerializer(comment_page["top_comments"], many=True, context=context).data,
                "comments": GameCommentSerializer(comment_page["comments"], many=True, context=context).data,
                "pagination": comment_page["pagination"],
            }
        )

    def post(self, request, pk):
        if not request.user.is_authenticated:
            return fail("로그인 후 댓글을 작성할 수 있습니다.", status=401)
        game = get_object_or_404(Game, pk=pk)
        serializer = GameCommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        parent = None
        parent_id = serializer.validated_data.get("parent_id")
        if parent_id:
            parent = get_object_or_404(GameComment, pk=parent_id, game=game)
            if parent.parent_id:
                parent = parent.parent
        comment = GameComment.objects.create(
            game=game,
            user=request.user,
            parent=parent,
            content=serializer.validated_data["content"],
        )
        comment = _comment_queryset(game, include_replies=True).get(pk=comment.pk)
        return ok(GameCommentSerializer(comment, context=_comment_context(game, [comment], request)).data, "댓글을 등록했습니다.", 201)


class UserCommentListView(APIView):
    def get(self, request, user_id):
        user = get_object_or_404(get_user_model().objects.select_related("steam_account"), pk=user_id)
        page_size = 10
        try:
            requested_page = max(1, int(request.query_params.get("page", 1)))
        except (TypeError, ValueError):
            requested_page = 1

        queryset = (
            GameComment.objects.filter(user=user)
            .select_related("game", "user", "user__profile", "user__steam_account")
            .annotate(
                like_count=Count("reactions", filter=Q(reactions__value=GameCommentReaction.LIKE), distinct=True),
                dislike_count=Count("reactions", filter=Q(reactions__value=GameCommentReaction.DISLIKE), distinct=True),
                reaction_count=Count("reactions", distinct=True),
            )
            .order_by("-created_at")
        )
        paginator = Paginator(queryset, page_size)
        total_pages = max(1, paginator.num_pages)
        page_number = min(requested_page, total_pages)
        try:
            page = paginator.page(page_number)
        except EmptyPage:
            page = paginator.page(total_pages)
            page_number = total_pages

        comments = list(page.object_list)
        return ok(
            {
                "user": _public_comment_user(user),
                "comments": GameCommentSerializer(comments, many=True, context=_user_comment_context(user, comments, request)).data,
                "pagination": {
                    "count": paginator.count,
                    "page": page_number,
                    "page_size": page_size,
                    "total_pages": total_pages,
                    "has_next": page.has_next(),
                    "has_previous": page.has_previous(),
                },
            }
        )


class GameCommentDetailView(APIView):
    def patch(self, request, pk, comment_pk):
        if not request.user.is_authenticated:
            return fail("로그인 후 댓글을 수정할 수 있습니다.", status=401)
        game = get_object_or_404(Game, pk=pk)
        comment = get_object_or_404(GameComment, pk=comment_pk, game=game)
        if comment.user_id != request.user.id:
            return fail("내 댓글만 수정할 수 있습니다.", status=403)
        serializer = GameCommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment.content = serializer.validated_data["content"]
        comment.save(update_fields=["content", "updated_at"])
        updated_comment = _comment_queryset(game, include_replies=True).get(pk=comment.pk)
        return ok(GameCommentSerializer(updated_comment, context=_comment_context(game, [updated_comment], request)).data)

    def delete(self, request, pk, comment_pk):
        if not request.user.is_authenticated:
            return fail("로그인 후 댓글을 삭제할 수 있습니다.", status=401)
        game = get_object_or_404(Game, pk=pk)
        comment = get_object_or_404(GameComment, pk=comment_pk, game=game)
        if comment.user_id != request.user.id:
            return fail("내 댓글만 삭제할 수 있습니다.", status=403)
        comment.delete()
        return ok(None, "댓글을 삭제했습니다.")


class GameCommentReactionView(APIView):
    def post(self, request, pk, comment_pk):
        if not request.user.is_authenticated:
            return fail("로그인 후 반응할 수 있습니다.", status=401)
        game = get_object_or_404(Game, pk=pk)
        comment = get_object_or_404(GameComment, pk=comment_pk, game=game)
        reaction = str(request.data.get("reaction", "")).lower().strip()
        value_map = {"like": GameCommentReaction.LIKE, "dislike": GameCommentReaction.DISLIKE}
        if reaction and reaction not in value_map:
            return fail("좋아요 또는 싫어요만 선택할 수 있습니다.")

        selected_value = value_map.get(reaction)
        existing = GameCommentReaction.objects.filter(comment=comment, user=request.user).first()
        if not selected_value:
            if existing:
                existing.delete()
        elif existing and existing.value == selected_value:
            existing.delete()
        else:
            GameCommentReaction.objects.update_or_create(
                comment=comment,
                user=request.user,
                defaults={"value": selected_value},
            )

        updated_comment = _comment_queryset(game, include_replies=True).get(pk=comment.pk)
        return ok(GameCommentSerializer(updated_comment, context=_comment_context(game, [updated_comment], request)).data)


def _comment_queryset(game, include_replies=False):
    queryset = (
        game.comments.select_related("game", "user", "user__profile", "user__steam_account")
        .annotate(
            like_count=Count("reactions", filter=Q(reactions__value=GameCommentReaction.LIKE), distinct=True),
            dislike_count=Count("reactions", filter=Q(reactions__value=GameCommentReaction.DISLIKE), distinct=True),
            reaction_count=Count("reactions", distinct=True),
        )
        .order_by("-created_at")
    )
    if not include_replies:
        queryset = queryset.filter(parent__isnull=True)
    return queryset


def _paginated_comments(game, request):
    page_size = 10
    try:
        requested_page = max(1, int(request.query_params.get("page", 1)))
    except (TypeError, ValueError):
        requested_page = 1

    queryset = _comment_queryset(game)
    top_comments = list(queryset.order_by("-reaction_count", "-created_at")[:3])
    top_ids = [comment.id for comment in top_comments]
    latest_queryset = queryset.exclude(id__in=top_ids).order_by("-created_at")
    paginator = Paginator(latest_queryset, page_size)
    total_pages = max(1, paginator.num_pages)
    page_number = min(requested_page, total_pages)
    try:
        page = paginator.page(page_number)
    except EmptyPage:
        page = paginator.page(total_pages)
        page_number = total_pages

    return {
        "total_count": game.comments.count(),
        "top_comments": top_comments,
        "comments": list(page.object_list),
        "pagination": {
            "count": paginator.count,
            "page": page_number,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page.has_next(),
            "has_previous": page.has_previous(),
        },
    }


def _comment_context(game, comments, request):
    comment_ids = [comment.id for comment in comments]
    reply_comments = list(
        GameComment.objects.filter(parent_id__in=comment_ids)
        .select_related("user", "user__profile", "user__steam_account")
    )
    visible_comments = list(comments) + reply_comments
    user_ids = [comment.user_id for comment in visible_comments]
    playtime_by_user = dict(
        UserGame.objects.filter(game=game, user_id__in=user_ids, source="steam").values_list("user_id", "playtime_minutes")
    )
    reaction_by_comment = {}
    if request.user.is_authenticated:
        reaction_by_comment = dict(
            GameCommentReaction.objects.filter(user=request.user, comment_id__in=[comment.id for comment in visible_comments]).values_list(
                "comment_id", "value"
            )
        )
    return {
        "request": request,
        "steam_playtime_by_user": playtime_by_user,
        "reaction_by_comment": reaction_by_comment,
    }


def _user_comment_context(user, comments, request):
    game_ids = [comment.game_id for comment in comments]
    playtime_by_game = dict(
        UserGame.objects.filter(user=user, game_id__in=game_ids, source="steam").values_list("game_id", "playtime_minutes")
    )
    reaction_by_comment = {}
    if request.user.is_authenticated:
        reaction_by_comment = dict(
            GameCommentReaction.objects.filter(user=request.user, comment_id__in=[comment.id for comment in comments]).values_list(
                "comment_id", "value"
            )
        )
    return {
        "request": request,
        "steam_playtime_by_comment": {comment.id: playtime_by_game.get(comment.game_id) for comment in comments},
        "reaction_by_comment": reaction_by_comment,
        "include_replies": False,
    }


def _public_comment_user(user):
    steam_account = getattr(user, "steam_account", None)
    return {
        "id": user.id,
        "name": user.username or user.email,
        "avatar_url": user_avatar_url(user),
        "steam_connected": bool(steam_account),
    }


class GamePricesView(APIView):
    def get(self, request, pk):
        game = Game.objects.get(pk=pk)
        try:
            sync_prices_for_game(game, history_days=730)
        except ItadApiError as exc:
            return fail(str(exc), status=502)
        return ok(GameDetailSerializer(game).data["prices"])


class GameOtherStorePricesView(APIView):
    def get(self, request, pk):
        game = Game.objects.get(pk=pk)
        try:
            return ok(itad_service.fetch_other_store_prices(game, limit=2))
        except ItadApiError as exc:
            return fail(str(exc), status=502)


class GameRelatedProductsView(APIView):
    def get(self, request, pk):
        game = Game.objects.get(pk=pk)
        if request.query_params.get("refresh") == "1":
            sync_related_products_for_game(game)
        return ok(_related_products_payload(game))


def _related_products_payload(game):
    products = list(game.related_products.select_related("linked_game").all())
    return {
        "dlc": sorted(
            [_related_product_item(product) for product in products if product.product_type == RelatedProduct.DLC],
            key=lambda item: (item["current_price"] <= 0 and not item["is_free"], item["current_price"], item["title"]),
        ),
        "bundles": sorted(
            [_related_product_item(product) for product in products if product.product_type == RelatedProduct.BUNDLE],
            key=lambda item: (item["current_price"], item["title"]),
        ),
    }


def _related_product_item(product):
    current_price = _normalize_related_price(product.current_price, product.product_type)
    original_price = _normalize_related_price(product.original_price, product.product_type)
    return {
        "id": product.external_id,
        "game_id": product.linked_game_id,
        "type": product.product_type,
        "title": product.title,
        "thumbnail": product.thumbnail,
        "current_price": current_price,
        "original_price": original_price,
        "discount_rate": product.discount_rate,
        "currency": product.currency,
        "url": product.url,
        "is_free": product.is_free,
        "included_count": product.included_count,
    }


def _normalize_related_price(value, product_type):
    value = int(value or 0)
    if product_type == RelatedProduct.DLC and value >= 100000:
        return value // 100
    if value >= 1000000:
        return value // 100
    return value


class GameHistoryView(APIView):
    def get(self, request, pk):
        game = Game.objects.prefetch_related("price_history__store").get(pk=pk)
        should_refresh = request.query_params.get("refresh") == "1" or _should_refresh_related_product_history(game)
        if should_refresh:
            try:
                sync_history_for_game(game, days=730)
            except ItadApiError as exc:
                if request.query_params.get("refresh") == "1":
                    return fail(str(exc), status=502)
        since = timezone.localdate() - timedelta(days=730)
        if game.release_date and game.release_date > since:
            since = game.release_date
        history = (
            game.price_history.filter(recorded_at__gte=since, store__name__iexact="Steam")
            .select_related("store")
            .order_by("recorded_at", "store__name")
        )
        return ok(PriceHistorySerializer(history, many=True).data)


def _should_refresh_related_product_history(game):
    if not game.related_product_entries.filter(product_type=RelatedProduct.DLC).exists():
        return False
    return game.price_history.filter(store__name__iexact="Steam").count() <= 1


class GameRecommendationView(APIView):
    def get(self, request, pk):
        game = Game.objects.prefetch_related("prices__store").get(pk=pk)
        if request.query_params.get("refresh") == "1":
            try:
                sync_prices_for_game(game, force=True, history_days=730)
            except ItadApiError as exc:
                return fail(str(exc), status=502)
        return ok(analyze_purchase(game))


class GameAIAnalysisView(APIView):
    def post(self, request, pk):
        game = Game.objects.prefetch_related("prices__store", "game_tags__tag").get(pk=pk)
        if request.user.is_authenticated:
            game = Game.objects.prefetch_related("prices__store", "genres", "game_tags__tag").get(pk=pk)
            analysis = get_or_create_personalized_ai_analysis(game, request.user)
        else:
            analysis = get_or_create_ai_analysis(game)
        return ok(GameAIAnalysisSerializer(analysis).data)
