from django.db import models


class Store(models.Model):
    name = models.CharField(max_length=120, unique=True)
    code = models.SlugField(max_length=80, unique=True)
    logo_url = models.URLField(blank=True)

    def __str__(self):
        return self.name


class Price(models.Model):
    game = models.ForeignKey("games.Game", on_delete=models.CASCADE, related_name="prices")
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="prices")
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_rate = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=8, default="KRW")
    url = models.URLField(blank=True)
    historical_low_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    historical_low_date = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("game", "store")
        ordering = ["current_price"]
        indexes = [
            models.Index(fields=["store", "current_price"]),
            models.Index(fields=["store", "discount_rate"]),
        ]

    def __str__(self):
        return f"{self.game} @ {self.store}"


class PriceHistory(models.Model):
    game = models.ForeignKey("games.Game", on_delete=models.CASCADE, related_name="price_history")
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="price_history")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_rate = models.PositiveIntegerField(default=0)
    recorded_at = models.DateField()

    class Meta:
        ordering = ["recorded_at"]
        unique_together = ("game", "store", "recorded_at")


class DiscountEvent(models.Model):
    game = models.ForeignKey("games.Game", on_delete=models.CASCADE, related_name="discount_events")
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="discount_events")
    started_at = models.DateField()
    ended_at = models.DateField(null=True, blank=True)
    discount_rate = models.PositiveIntegerField(default=0)
    low_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["-started_at"]


class EpicFreeGame(models.Model):
    title = models.CharField(max_length=220)
    thumbnail = models.URLField(blank=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    claim_url = models.URLField(blank=True)
    source = models.CharField(max_length=40, default="mock")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

