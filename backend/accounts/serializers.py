import re

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers

from .models import EmailVerificationCode, UserGame, UserSteamAccount
from .utils import user_avatar_url

User = get_user_model()


def validate_complex_password(value, user=None):
    if not re.match(r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$", value or ""):
        raise serializers.ValidationError("비밀번호는 8자리 이상이며 영문, 숫자, 특수문자를 모두 포함해야 합니다.")
    validate_password(value, user)


class UserSerializer(serializers.ModelSerializer):
    steam_connected = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    has_usable_password = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "display_name",
            "avatar_url",
            "steam_connected",
            "has_usable_password",
        ]

    def get_steam_connected(self, obj):
        return hasattr(obj, "steam_account")

    def get_display_name(self, obj):
        return obj.username or obj.email

    def get_avatar_url(self, obj):
        return user_avatar_url(obj, self.context.get("request"))

    def get_has_usable_password(self, obj):
        return obj.has_usable_password()


class AccountDeleteSerializer(serializers.Serializer):
    confirmation = serializers.CharField()
    password = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate(self, attrs):
        user = self.context["request"].user
        confirmation = attrs.get("confirmation", "").strip()
        password = attrs.get("password", "")
        if confirmation != "회원탈퇴":
            raise serializers.ValidationError("회원탈퇴를 정확히 입력해 주세요.")
        if user.has_usable_password() and not user.check_password(password):
            raise serializers.ValidationError("비밀번호가 올바르지 않습니다.")
        attrs["confirmation"] = confirmation
        return attrs


class AccountPasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=False, allow_blank=True, write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.context["request"].user
        current_password = attrs.get("current_password", "")
        new_password = attrs.get("new_password", "")
        new_password_confirm = attrs.get("new_password_confirm", "")

        if user.has_usable_password() and not user.check_password(current_password):
            raise serializers.ValidationError("현재 비밀번호가 올바르지 않습니다.")
        if new_password != new_password_confirm:
            raise serializers.ValidationError("새 비밀번호가 일치하지 않습니다.")

        validate_complex_password(new_password, user)
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    email_verification_code = serializers.CharField(write_only=True, min_length=6, max_length=6)
    username = serializers.CharField(required=False, allow_blank=True)

    def validate_email(self, value):
        email = value.lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("이미 사용 중인 이메일입니다.")
        return email

    def validate_password(self, value):
        validate_complex_password(value)
        return value

    def validate_username(self, value):
        username = value.strip()
        if username and len(username) < 2:
            raise serializers.ValidationError("닉네임은 2자 이상이어야 합니다.")
        if username and User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError("이미 사용 중인 닉네임입니다.")
        return username

    def validate(self, attrs):
        email = attrs["email"].lower()
        code = attrs["email_verification_code"].strip()
        verification = EmailVerificationCode.objects.filter(email__iexact=email).first()
        if not verification:
            raise serializers.ValidationError("이메일 인증코드를 먼저 받아 주세요.")
        if verification.is_expired:
            raise serializers.ValidationError("이메일 인증코드가 만료되었습니다. 다시 받아 주세요.")
        if verification.attempts >= 5:
            raise serializers.ValidationError("인증코드 입력 횟수를 초과했습니다. 다시 받아 주세요.")
        if verification.code != code:
            verification.attempts += 1
            verification.save(update_fields=["attempts"])
            raise serializers.ValidationError("이메일 인증코드가 올바르지 않습니다.")
        if not verification.verified_at:
            raise serializers.ValidationError("이메일 인증 확인을 먼저 완료해 주세요.")
        attrs["_email_verification"] = verification
        return attrs

    def create(self, validated_data):
        email = validated_data["email"]
        username = validated_data.get("username") or email.split("@")[0]
        verification = validated_data.pop("_email_verification")
        validated_data.pop("email_verification_code", None)
        user = User.objects.create_user(username=username, email=email, password=validated_data["password"])
        verification.verified_at = verification.verified_at or timezone.now()
        verification.save(update_fields=["verified_at"])
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = User.objects.filter(email__iexact=attrs["email"]).first()
        if not user:
            raise serializers.ValidationError("이메일 또는 비밀번호가 올바르지 않습니다.")
        auth_user = authenticate(username=user.username, password=attrs["password"])
        if not auth_user:
            raise serializers.ValidationError("이메일 또는 비밀번호가 올바르지 않습니다.")
        attrs["user"] = auth_user
        return attrs


class SteamConnectSerializer(serializers.Serializer):
    steam_id_or_url = serializers.CharField()


class UserGameCreateSerializer(serializers.Serializer):
    game_id = serializers.IntegerField()
    playtime_minutes = serializers.IntegerField(required=False, min_value=0, default=0)


class UserSteamAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSteamAccount
        fields = ["steam_id", "profile_url", "persona_name", "avatar_url", "library_synced_at"]


class UserGameSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="game.title")
    thumbnail = serializers.URLField(source="game.thumbnail")
    steam_app_id = serializers.CharField(source="game.steam_app_id")

    class Meta:
        model = UserGame
        fields = ["id", "title", "thumbnail", "steam_app_id", "playtime_minutes", "source", "synced_at"]
