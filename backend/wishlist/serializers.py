from rest_framework import serializers

from games.serializers import GameCardSerializer
from .models import UserWishlist


class UserWishlistSerializer(serializers.ModelSerializer):
    game = GameCardSerializer(read_only=True)
    game_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = UserWishlist
        fields = ["id", "game", "game_id", "target_price", "created_at"]

