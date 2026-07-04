import uuid
from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils import timezone


def profile_avatar_upload_to(instance, filename):
    extension = Path(filename).suffix.lower()[:10]
    return f"profile_avatars/user_{instance.user_id}{extension}"


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    avatar = models.FileField(upload_to=profile_avatar_upload_to, blank=True)
    use_default_avatar = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} profile"


class UserSteamAccount(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="steam_account")
    steam_id = models.CharField(max_length=64, unique=True)
    profile_url = models.URLField(blank=True)
    persona_name = models.CharField(max_length=160, blank=True)
    avatar_url = models.URLField(blank=True)
    library_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.steam_id}"


class UserGame(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_games")
    game = models.ForeignKey("games.Game", on_delete=models.CASCADE, related_name="owners")
    playtime_minutes = models.PositiveIntegerField(default=0)
    source = models.CharField(max_length=40, default="steam")
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "game")


class EmailVerificationToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="email_verification_tokens")
    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at


class EmailVerificationCode(models.Model):
    email = models.EmailField(db_index=True)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

