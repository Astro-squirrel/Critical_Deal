from django.conf import settings
from django.db import models


class Genre(models.Model):
    name = models.CharField(max_length=80, unique=True)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=80, unique=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"], name="games_tag_name_idx"),
        ]

    def __str__(self):
        return self.name


class Developer(models.Model):
    name = models.CharField(max_length=160, unique=True)

    def __str__(self):
        return self.name


class Publisher(models.Model):
    name = models.CharField(max_length=160, unique=True)

    def __str__(self):
        return self.name


class Game(models.Model):
    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True)
    steam_app_id = models.CharField(max_length=40, blank=True)
    itad_plain = models.CharField(max_length=160, blank=True)
    thumbnail = models.URLField(blank=True)
    hero_image = models.URLField(blank=True)
    short_description = models.TextField(blank=True)
    release_date = models.DateField(null=True, blank=True)
    genres = models.ManyToManyField(Genre, blank=True)
    tags = models.ManyToManyField(Tag, through="GameTag", blank=True, related_name="games")
    developers = models.ManyToManyField(Developer, blank=True)
    publishers = models.ManyToManyField(Publisher, blank=True)
    popularity_score = models.PositiveIntegerField(default=0)
    steam_review_score = models.PositiveSmallIntegerField(default=0)
    steam_review_count = models.PositiveIntegerField(default=0)
    steam_reviews_updated_at = models.DateTimeField(null=True, blank=True)
    tags_updated_at = models.DateTimeField(null=True, blank=True)
    related_products_updated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        indexes = [
            models.Index(fields=["title"], name="games_game_title_b7a574_idx"),
            models.Index(fields=["slug"], name="games_game_slug_161310_idx"),
            models.Index(fields=["steam_review_score"], name="games_game_steam_r_8037c2_idx"),
            models.Index(fields=["steam_review_count"], name="games_game_steam_r_19972a_idx"),
        ]

    def __str__(self):
        return self.title


class GameTag(models.Model):
    STEAM = "steam"
    SOURCES = [(STEAM, "Steam")]

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="game_tags")
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name="game_tags")
    rank = models.PositiveSmallIntegerField(default=0)
    weight = models.PositiveSmallIntegerField(default=0)
    source = models.CharField(max_length=40, choices=SOURCES, default=STEAM)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["rank", "tag__name"]
        unique_together = ("game", "tag")
        indexes = [
            models.Index(fields=["game", "rank"], name="games_gt_game_rank_idx"),
            models.Index(fields=["tag"], name="games_gt_tag_idx"),
            models.Index(fields=["source"], name="games_gt_source_idx"),
        ]

    def __str__(self):
        return f"{self.game} - {self.tag}"


class RelatedProduct(models.Model):
    DLC = "dlc"
    BUNDLE = "bundle"
    PRODUCT_TYPES = [(DLC, "DLC"), (BUNDLE, "Bundle")]

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="related_products")
    linked_game = models.ForeignKey(
        Game,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="related_product_entries",
    )
    product_type = models.CharField(max_length=12, choices=PRODUCT_TYPES)
    external_id = models.CharField(max_length=40)
    title = models.CharField(max_length=240)
    thumbnail = models.URLField(blank=True)
    current_price = models.PositiveIntegerField(default=0)
    original_price = models.PositiveIntegerField(default=0)
    discount_rate = models.PositiveSmallIntegerField(default=0)
    currency = models.CharField(max_length=8, default="KRW")
    url = models.URLField(blank=True)
    is_free = models.BooleanField(default=False)
    included_count = models.PositiveIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["product_type", "current_price", "title"]
        unique_together = ("game", "product_type", "external_id")
        indexes = [
            models.Index(fields=["game", "product_type"], name="games_relat_game_id_348ed1_idx"),
            models.Index(fields=["product_type", "discount_rate"], name="games_relat_product_17a0bc_idx"),
        ]

    def __str__(self):
        return f"{self.game} - {self.title}"


class PlayerSnapshot(models.Model):
    STEAM = "steam"
    STEAMCHARTS = "steamcharts"
    SOURCES = [(STEAM, "Steam"), (STEAMCHARTS, "SteamCharts")]

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="player_history")
    players = models.PositiveIntegerField(default=0)
    recorded_at = models.DateTimeField()
    source = models.CharField(max_length=40, choices=SOURCES, default=STEAM)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["recorded_at"]
        unique_together = ("game", "source", "recorded_at")
        indexes = [
            models.Index(fields=["game", "recorded_at"], name="games_player_game_time_idx"),
            models.Index(fields=["source", "recorded_at"], name="games_player_source_time_idx"),
        ]

    def __str__(self):
        return f"{self.game} - {self.players} players at {self.recorded_at}"


class GameComment(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="game_comments")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, related_name="replies", null=True, blank=True)
    content = models.TextField(max_length=1200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["game", "-created_at"], name="games_comment_game_time_idx"),
            models.Index(fields=["game", "parent", "-created_at"], name="games_comment_thread_idx"),
            models.Index(fields=["user", "-created_at"], name="games_comment_user_time_idx"),
        ]

    def __str__(self):
        return f"{self.game} - {self.user}"


class GameCommentReaction(models.Model):
    LIKE = 1
    DISLIKE = -1
    REACTION_CHOICES = [(LIKE, "Like"), (DISLIKE, "Dislike")]

    comment = models.ForeignKey(GameComment, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="game_comment_reactions")
    value = models.SmallIntegerField(choices=REACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("comment", "user")
        indexes = [
            models.Index(fields=["comment", "value"], name="games_react_comment_val_idx"),
            models.Index(fields=["user", "value"], name="games_react_user_val_idx"),
        ]

    def __str__(self):
        return f"{self.comment_id} - {self.user_id} - {self.value}"

