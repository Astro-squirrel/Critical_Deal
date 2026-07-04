from decimal import Decimal
from datetime import timedelta

from django.db.models import Count, Max, Q
from django.utils import timezone
from rest_framework import serializers

from accounts.utils import user_avatar_url
from external_apis.services import ItadApiError, itad_service, steam_service
from prices.models import Price, PriceHistory
from prices.serializers import PriceSerializer
from .models import Game, GameComment, GameCommentReaction, GameTag, Genre, PlayerSnapshot


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["id", "name"]


class GameTagSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="tag.id")
    name = serializers.CharField(source="tag.name")

    class Meta:
        model = GameTag
        fields = ["id", "name", "rank", "weight", "source"]


class GameCardSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)
    tags = serializers.SerializerMethodField()
    best_price = serializers.SerializerMethodField()
    original_price = serializers.SerializerMethodField()
    max_discount = serializers.SerializerMethodField()
    platform = serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = [
            "id",
            "title",
            "slug",
            "steam_app_id",
            "thumbnail",
            "hero_image",
            "short_description",
            "release_date",
            "genres",
            "tags",
            "platform",
            "best_price",
            "original_price",
            "max_discount",
            "steam_review_score",
            "steam_review_count",
        ]

    def get_best_price(self, obj):
        if hasattr(obj, "best_price"):
            return obj.best_price
        prices = self._steam_prices(obj, "current_price")
        price = prices[0] if prices else None
        return price.current_price if price else None

    def get_original_price(self, obj):
        prices = self._steam_prices(obj, "-discount_rate")
        price = prices[0] if prices else None
        return price.original_price if price else None

    def get_max_discount(self, obj):
        if hasattr(obj, "max_discount"):
            return obj.max_discount or 0
        prices = self._steam_prices(obj, "-discount_rate")
        price = prices[0] if prices else None
        return price.discount_rate if price else 0

    def get_platform(self, obj):
        prices = self._steam_prices(obj)
        price = prices[0] if prices else None
        return price.store.name if price else "Steam"

    def get_tags(self, obj):
        prefetched = getattr(obj, "_prefetched_objects_cache", {})
        if "game_tags" in prefetched:
            game_tags = sorted(prefetched["game_tags"], key=lambda item: (item.rank, item.tag.name))
        else:
            game_tags = obj.game_tags.select_related("tag").order_by("rank", "tag__name")
        return GameTagSerializer(game_tags[:20], many=True).data

    def _steam_prices(self, obj, ordering=None):
        prefetched = getattr(obj, "_prefetched_objects_cache", {})
        if "prices" in prefetched:
            prices = [price for price in prefetched["prices"] if price.store.name.lower() == "steam"]
            if ordering == "current_price":
                return sorted(prices, key=lambda price: price.current_price)
            if ordering == "-discount_rate":
                return sorted(prices, key=lambda price: price.discount_rate, reverse=True)
            return prices
        queryset = obj.prices.filter(store__name__iexact="Steam").select_related("store")
        if ordering:
            queryset = queryset.order_by(ordering)
        return list(queryset)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        fallback_image = self._steam_header_image(instance) if instance.steam_app_id else ""
        if not data.get("thumbnail"):
            data["thumbnail"] = fallback_image
        if not data.get("hero_image"):
            data["hero_image"] = data.get("thumbnail") or fallback_image
        return data

    def _steam_header_image(self, obj):
        return f"https://cdn.akamai.steamstatic.com/steam/apps/{obj.steam_app_id}/header.jpg"


class GameDetailSerializer(GameCardSerializer):
    prices = serializers.SerializerMethodField()
    historical_low = serializers.SerializerMethodField()
    other_store_prices = serializers.SerializerMethodField()
    current_players = serializers.SerializerMethodField()
    peak_players = serializers.SerializerMethodField()
    player_history = serializers.SerializerMethodField()

    class Meta(GameCardSerializer.Meta):
        fields = GameCardSerializer.Meta.fields + [
            "itad_plain",
            "release_date",
            "prices",
            "historical_low",
            "other_store_prices",
            "current_players",
            "peak_players",
            "player_history",
        ]

    def get_historical_low(self, obj):
        price = obj.prices.filter(store__name__iexact="Steam").order_by("historical_low_price").first()
        return price.historical_low_price if price else None

    def get_prices(self, obj):
        return PriceSerializer(obj.prices.filter(store__name__iexact="Steam"), many=True).data

    def get_other_store_prices(self, obj):
        if self.context.get("include_other_store_prices") is False:
            return []
        try:
            return itad_service.fetch_other_store_prices(obj, limit=2)
        except ItadApiError:
            return []

    def get_current_players(self, obj):
        latest = self._player_history(obj).order_by("-recorded_at").first()
        if latest:
            return latest.players
        return steam_service.fetch_current_players(obj.steam_app_id)

    def get_peak_players(self, obj):
        return self._player_history(obj).aggregate(peak=Max("players")).get("peak")

    def get_player_history(self, obj):
        daily = {}
        for snapshot in self._player_history(obj).order_by("recorded_at"):
            local_date = timezone.localtime(snapshot.recorded_at).date()
            bucket = daily.setdefault(local_date, {"total": 0, "count": 0})
            bucket["total"] += int(snapshot.players or 0)
            bucket["count"] += 1
        return [
            {
                "players": round(bucket["total"] / bucket["count"]),
                "recorded_at": recorded_date.isoformat(),
                "source": "daily_average",
            }
            for recorded_date, bucket in sorted(daily.items())
            if bucket["count"]
        ]

    def _player_history(self, obj):
        since = timezone.now() - timedelta(days=14)
        return obj.player_history.filter(recorded_at__gte=since)


class PlayerSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlayerSnapshot
        fields = ["players", "recorded_at", "source"]


class PriceHistorySerializer(serializers.ModelSerializer):
    store = serializers.CharField(source="store.name")
    original_price = serializers.SerializerMethodField()

    class Meta:
        model = PriceHistory
        fields = ["store", "price", "original_price", "discount_rate", "recorded_at"]

    def get_original_price(self, obj):
        if not obj.discount_rate:
            return obj.price
        rate = Decimal("1") - (Decimal(obj.discount_rate) / Decimal("100"))
        if rate <= 0:
            return obj.price
        return (obj.price / rate).quantize(Decimal("1"))


class GameCommentSerializer(serializers.ModelSerializer):
    author_id = serializers.IntegerField(source="user_id", read_only=True)
    author_name = serializers.SerializerMethodField()
    author_avatar_url = serializers.SerializerMethodField()
    author_steam_connected = serializers.SerializerMethodField()
    parent_id = serializers.IntegerField(read_only=True)
    game = serializers.SerializerMethodField()
    steam_playtime_minutes = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    dislike_count = serializers.SerializerMethodField()
    my_reaction = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = GameComment
        fields = [
            "id",
            "content",
            "parent_id",
            "author_id",
            "author_name",
            "author_avatar_url",
            "author_steam_connected",
            "game",
            "steam_playtime_minutes",
            "like_count",
            "dislike_count",
            "my_reaction",
            "can_edit",
            "replies",
            "created_at",
            "updated_at",
        ]

    def get_author_name(self, obj):
        return obj.user.username or obj.user.email

    def get_author_avatar_url(self, obj):
        return user_avatar_url(obj.user, self.context.get("request"))

    def get_author_steam_connected(self, obj):
        return hasattr(obj.user, "steam_account")

    def get_game(self, obj):
        return {
            "id": obj.game_id,
            "title": obj.game.title,
            "thumbnail": obj.game.thumbnail,
            "hero_image": obj.game.hero_image,
            "steam_app_id": obj.game.steam_app_id,
        }

    def get_replies(self, obj):
        if obj.parent_id or not self.context.get("include_replies", True):
            return []
        queryset = (
            obj.replies.select_related("game", "user", "user__profile", "user__steam_account")
            .annotate(
                like_count=Count("reactions", filter=Q(reactions__value=GameCommentReaction.LIKE), distinct=True),
                dislike_count=Count("reactions", filter=Q(reactions__value=GameCommentReaction.DISLIKE), distinct=True),
            )
            .order_by("created_at")
        )
        return GameCommentSerializer(queryset, many=True, context=self.context).data

    def get_steam_playtime_minutes(self, obj):
        playtime_by_comment = self.context.get("steam_playtime_by_comment", {})
        if obj.id in playtime_by_comment:
            return playtime_by_comment.get(obj.id)
        return self.context.get("steam_playtime_by_user", {}).get(obj.user_id)

    def get_like_count(self, obj):
        if hasattr(obj, "like_count"):
            return obj.like_count
        return obj.reactions.filter(value=1).count()

    def get_dislike_count(self, obj):
        if hasattr(obj, "dislike_count"):
            return obj.dislike_count
        return obj.reactions.filter(value=-1).count()

    def get_my_reaction(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return ""
        value = self.context.get("reaction_by_comment", {}).get(obj.id)
        if value == 1:
            return "like"
        if value == -1:
            return "dislike"
        return ""

    def get_can_edit(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and obj.user_id == request.user.id)


class GameCommentCreateSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=1200, trim_whitespace=True)
    parent_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError("댓글 내용을 입력해 주세요.")
        return value.strip()
