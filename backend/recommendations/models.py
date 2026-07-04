from django.conf import settings
from django.db import models


class Recommendation(models.Model):
    BUY = "BUY"
    CONSIDER = "CONSIDER"
    WAIT = "WAIT"
    DECISIONS = [(BUY, "Buy"), (CONSIDER, "Consider"), (WAIT, "Wait")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="recommendations")
    game = models.ForeignKey("games.Game", on_delete=models.CASCADE, related_name="recommendations")
    score = models.PositiveIntegerField(default=0)
    decision = models.CharField(max_length=20, choices=DECISIONS, default=WAIT)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class RecommendationAnalysis(models.Model):
    recommendation = models.OneToOneField(Recommendation, on_delete=models.CASCADE, related_name="analysis")
    current_vs_low_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    days_since_last_discount = models.PositiveIntegerField(default=0)
    average_discount_interval = models.PositiveIntegerField(default=0)
    discount_frequency = models.PositiveIntegerField(default=0)
    platform_price_rank = models.PositiveIntegerField(default=1)
    pattern_label = models.CharField(max_length=40, default="UNKNOWN")
    explanation = models.TextField()


class GameAIAnalysis(models.Model):
    game = models.OneToOneField("games.Game", on_delete=models.CASCADE, related_name="ai_analysis")
    score = models.PositiveIntegerField(default=0)
    decision = models.CharField(max_length=20, choices=Recommendation.DECISIONS, default=Recommendation.WAIT)
    recommendation_text = models.TextField()
    pattern_label = models.CharField(max_length=40, default="UNKNOWN")
    pattern_analysis = models.TextField()
    metrics = models.JSONField(default=dict, blank=True)
    price_fingerprint = models.CharField(max_length=64)
    prompt_version = models.CharField(max_length=40)
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-generated_at"]
        indexes = [
            models.Index(fields=["game", "generated_at"], name="recommenda_game_id_de2a3c_idx"),
            models.Index(fields=["price_fingerprint", "prompt_version"], name="recommenda_price_f_80b28c_idx"),
        ]


class UserGameAIAnalysis(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="game_ai_analyses")
    game = models.ForeignKey("games.Game", on_delete=models.CASCADE, related_name="user_ai_analyses")
    score = models.PositiveIntegerField(default=0)
    price_score = models.PositiveIntegerField(default=0)
    taste_score = models.PositiveIntegerField(default=0)
    quality_score = models.PositiveIntegerField(default=0)
    decision = models.CharField(max_length=20, choices=Recommendation.DECISIONS, default=Recommendation.WAIT)
    recommendation_text = models.TextField()
    price_reason = models.TextField()
    taste_reason = models.TextField()
    pattern_label = models.CharField(max_length=40, default="UNKNOWN")
    pattern_analysis = models.TextField()
    metrics = models.JSONField(default=dict, blank=True)
    input_fingerprint = models.CharField(max_length=64)
    prompt_version = models.CharField(max_length=40)
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-generated_at"]
        unique_together = ("user", "game")
        indexes = [
            models.Index(fields=["user", "game", "generated_at"], name="recommenda_user_id_48e4b9_idx"),
            models.Index(fields=["input_fingerprint", "prompt_version"], name="recommenda_input_f_9bc8f6_idx"),
        ]

