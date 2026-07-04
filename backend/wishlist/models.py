from django.conf import settings
from django.db import models


class UserWishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist_items")
    game = models.ForeignKey("games.Game", on_delete=models.CASCADE, related_name="wishlisted_by")
    target_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "game")
        ordering = ["-created_at"]

