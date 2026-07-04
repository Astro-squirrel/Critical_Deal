from rest_framework import serializers

from .models import EpicFreeGame, Price, Store


class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ["id", "name", "code", "logo_url"]


class PriceSerializer(serializers.ModelSerializer):
    store = StoreSerializer(read_only=True)

    class Meta:
        model = Price
        fields = [
            "id",
            "store",
            "current_price",
            "original_price",
            "discount_rate",
            "currency",
            "url",
            "historical_low_price",
            "historical_low_date",
            "updated_at",
        ]


class EpicFreeGameSerializer(serializers.ModelSerializer):
    class Meta:
        model = EpicFreeGame
        fields = ["id", "title", "thumbnail", "starts_at", "ends_at", "claim_url", "source"]

