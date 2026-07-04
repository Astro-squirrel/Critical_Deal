from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.responses import ok
from .models import UserWishlist
from .serializers import UserWishlistSerializer


class WishlistView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = request.user.wishlist_items.select_related("game").prefetch_related("game__genres", "game__prices__store")
        return ok(UserWishlistSerializer(items, many=True).data)

    def post(self, request):
        serializer = UserWishlistSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item, _ = UserWishlist.objects.get_or_create(
            user=request.user,
            game_id=serializer.validated_data["game_id"],
            defaults={"target_price": serializer.validated_data.get("target_price")},
        )
        return ok(UserWishlistSerializer(item).data, "찜 목록에 추가했습니다.", 201)


class WishlistDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        request.user.wishlist_items.filter(pk=pk).delete()
        return ok(None, "찜 항목을 삭제했습니다.")

