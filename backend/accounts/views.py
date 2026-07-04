import re
import secrets
from datetime import timedelta
import requests
from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.core.exceptions import ValidationError
from django.core.mail import send_mail as django_send_mail
from django.core.validators import validate_email
from django.middleware.csrf import get_token
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.text import slugify
from django.utils import timezone
from urllib.parse import urlencode
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.views import APIView

from common.responses import fail, ok
from external_apis.services import steam_service
from games.models import Game
from .models import EmailVerificationCode, EmailVerificationToken, UserGame, UserProfile, UserSteamAccount
from .serializers import (
    AccountDeleteSerializer,
    AccountPasswordChangeSerializer,
    LoginSerializer,
    SignupSerializer,
    SteamConnectSerializer,
    UserGameCreateSerializer,
    UserGameSerializer,
    UserSerializer,
    UserSteamAccountSerializer,
)
from .steam_openid import SteamOpenIdError, build_steam_login_url, frontend_url, verify_steam_callback

User = get_user_model()
ALLOWED_AVATAR_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_AVATAR_SIZE = 3 * 1024 * 1024


def send_mail(subject, message, from_email=None, recipient_list=None, fail_silently=False, **kwargs):
    recipients = recipient_list or []
    if settings.EMAIL_API_PROVIDER == "resend" or settings.RESEND_API_KEY:
        if not settings.RESEND_API_KEY:
            if fail_silently:
                return 0
            raise RuntimeError("RESEND_API_KEY가 설정되지 않았습니다.")

        code_match = re.search(r"(?<!\d)\d{6}(?!\d)", message or "")
        if code_match:
            code = code_match.group(0)
            subject = "Critical Deal 이메일 인증코드"
            message = (
                "Critical Deal 회원가입 이메일 인증코드입니다.\n\n"
                f"인증코드: {code}\n\n"
                "이 코드는 10분 동안 유효합니다. 본인이 요청하지 않았다면 이 메일을 무시해 주세요."
            )

        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": settings.RESEND_FROM_EMAIL,
                "to": recipients,
                "subject": subject,
                "text": message,
            },
            timeout=settings.EMAIL_TIMEOUT,
        )
        if response.status_code >= 400:
            if fail_silently:
                return 0
            raise RuntimeError(f"Resend API 오류({response.status_code}): {response.text}")
        return 1

    return django_send_mail(subject, message, from_email, recipient_list, fail_silently=fail_silently, **kwargs)


class SignupView(APIView):
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request, user)
        get_token(request)
        return ok(UserSerializer(user, context={"request": request}).data, "회원가입이 완료되었습니다.", 201)


class UsernameCheckView(APIView):
    def get(self, request):
        username = request.query_params.get("username", "").strip()
        if not username:
            return ok({"available": False, "message": "닉네임을 입력해 주세요."})
        if len(username) < 2:
            return ok({"available": False, "message": "닉네임은 2자 이상이어야 합니다."})
        queryset = User.objects.filter(username__iexact=username)
        if request.user.is_authenticated:
            queryset = queryset.exclude(pk=request.user.pk)
        exists = queryset.exists()
        message = "사용 가능한 닉네임입니다." if not exists else "이미 사용 중인 닉네임입니다."
        return ok({"available": not exists, "message": message})


class EmailCheckView(APIView):
    def get(self, request):
        email = request.query_params.get("email", "").strip().lower()
        if not email:
            return ok({"available": False, "message": "이메일을 입력해 주세요."})
        try:
            validate_email(email)
        except ValidationError:
            return ok({"available": False, "message": "올바른 이메일 형식이 아닙니다."})

        exists = User.objects.filter(email__iexact=email).exists()
        message = "사용 가능한 이메일입니다." if not exists else "이미 사용 중인 이메일입니다."
        return ok({"available": not exists, "message": message})


class EmailCodeSendView(APIView):
    def post(self, request):
        email = str(request.data.get("email", "")).strip().lower()
        if not email:
            return fail("이메일을 입력해 주세요.")
        try:
            validate_email(email)
        except ValidationError:
            return fail("올바른 이메일 형식이 아닙니다.")
        if User.objects.filter(email__iexact=email).exists():
            return fail("이미 사용 중인 이메일입니다.")

        code = f"{secrets.randbelow(1000000):06d}"
        EmailVerificationCode.objects.filter(email__iexact=email, verified_at__isnull=True).update(expires_at=timezone.now())
        verification = EmailVerificationCode.objects.create(
            email=email,
            code=code,
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        try:
            send_mail(
                "Critical Deal 이메일 인증코드",
                (
                    "Critical Deal 회원가입 이메일 인증코드입니다.\n\n"
                    f"인증코드: {code}\n\n"
                    "이 코드는 10분 동안 유효합니다. 본인이 요청하지 않았다면 이 메일을 무시해 주세요."
                ),
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
        except Exception as exc:
            verification.delete()
            return fail(f"이메일 발송에 실패했습니다: {exc}", status=502)
        return ok({"expires_in_seconds": 600}, "인증코드를 이메일로 보냈습니다.")


class EmailCodeVerifyView(APIView):
    def post(self, request):
        email = str(request.data.get("email", "")).strip().lower()
        code = str(request.data.get("code", "")).strip()
        if not email or not code:
            return fail("이메일과 인증코드를 입력해 주세요.")
        try:
            validate_email(email)
        except ValidationError:
            return fail("올바른 이메일 형식이 아닙니다.")

        verification = EmailVerificationCode.objects.filter(email__iexact=email).first()
        if not verification:
            return fail("인증코드를 먼저 받아 주세요.")
        if verification.verified_at:
            return ok({"verified": True}, "이미 인증된 코드입니다.")
        if verification.is_expired:
            return fail("인증코드가 만료되었습니다. 다시 받아 주세요.")
        if verification.attempts >= 5:
            return fail("인증코드 입력 횟수를 초과했습니다. 다시 받아 주세요.")
        if verification.code != code:
            verification.attempts += 1
            verification.save(update_fields=["attempts"])
            return fail("인증코드가 올바르지 않습니다.")

        verification.verified_at = timezone.now()
        verification.save(update_fields=["verified_at"])
        return ok({"verified": True}, "이메일 인증이 완료되었습니다.")


class CsrfTokenView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return ok({"csrf_token": get_token(request)})


class EmailVerifyView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, token):
        verification = EmailVerificationToken.objects.select_related("user").filter(token=token, verified_at__isnull=True).first()
        if not verification:
            return redirect(frontend_url("/login?email_verified=invalid"))
        if verification.is_expired:
            return redirect(frontend_url("/login?email_verified=expired"))

        verification.verified_at = timezone.now()
        verification.save(update_fields=["verified_at"])
        return redirect(frontend_url("/login?email_verified=1"))


class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        get_token(request)
        return ok(UserSerializer(user, context={"request": request}).data, "로그인되었습니다.")


class SteamLoginStartView(APIView):
    def get(self, request):
        return ok({"auth_url": build_steam_login_url(request)})


class SteamLoginCallbackView(APIView):
    def get(self, request):
        try:
            steam_id = verify_steam_callback(request)
        except SteamOpenIdError as exc:
            return redirect(frontend_url(f"/login?{urlencode({'steam_error': str(exc)})}"))

        account = UserSteamAccount.objects.select_related("user").filter(steam_id=steam_id).first()
        if account:
            user = account.user
        else:
            user = self._create_steam_user(steam_id)
            UserSteamAccount.objects.create(
                user=user,
                steam_id=steam_id,
                profile_url=f"https://steamcommunity.com/profiles/{steam_id}",
                persona_name=user.username,
            )

        sync_steam_account(user, steam_id)
        login(request, user)
        get_token(request)
        return redirect(frontend_url("/"))

    def _create_steam_user(self, steam_id):
        base_username = f"steam_{steam_id}"
        username = base_username
        suffix = 1
        while User.objects.filter(username__iexact=username).exists():
            suffix += 1
            username = f"{base_username}_{suffix}"

        user = User(username=username, email=f"{username}@steam.local")
        user.set_unusable_password()
        user.save()
        return user


class LogoutView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        logout(request)
        return ok(None, "로그아웃되었습니다.")


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return ok(UserSerializer(request.user, context={"request": request}).data)


class AccountDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        serializer = AccountDeleteSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        logout(request)
        user.delete()
        return ok(None, "회원탈퇴가 완료되었습니다.")


class AccountPasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AccountPasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logout(request)
        return ok(None, "비밀번호가 변경되었습니다. 다시 로그인해 주세요.")


class AccountProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def patch(self, request):
        user = request.user
        username = str(request.data.get("username", user.username)).strip()
        if len(username) < 2:
            return fail("닉네임은 2자 이상이어야 합니다.")
        if len(username) > 150:
            return fail("닉네임은 150자 이하로 입력해 주세요.")
        if not re.match(r"^[\w.@+-]+$", username):
            return fail("닉네임에는 문자, 숫자, @/./+/-/_만 사용할 수 있습니다.")
        if User.objects.filter(username__iexact=username).exclude(pk=user.pk).exists():
            return fail("이미 사용 중인 닉네임입니다.")

        profile, _ = UserProfile.objects.get_or_create(user=user)
        avatar = request.FILES.get("avatar")
        clear_avatar = str(request.data.get("clear_avatar", "")).lower() in {"1", "true", "yes"}

        if avatar:
            extension = "." + avatar.name.rsplit(".", 1)[-1].lower() if "." in avatar.name else ""
            content_type = getattr(avatar, "content_type", "")
            if extension not in ALLOWED_AVATAR_EXTENSIONS or content_type not in ALLOWED_AVATAR_TYPES:
                return fail("프로필 사진은 jpg, png, webp, gif 파일만 사용할 수 있습니다.")
            if avatar.size > MAX_AVATAR_SIZE:
                return fail("프로필 사진은 3MB 이하로 업로드해 주세요.")

        if user.username != username:
            user.username = username
            user.save(update_fields=["username"])

        if clear_avatar and profile.avatar:
            profile.avatar.delete(save=False)
            profile.avatar = ""
        if clear_avatar:
            profile.use_default_avatar = True

        if avatar:
            if profile.avatar:
                profile.avatar.delete(save=False)
            profile.avatar = avatar
            profile.use_default_avatar = False

        if avatar or clear_avatar:
            profile.save()

        return ok(UserSerializer(user, context={"request": request}).data, "프로필이 저장되었습니다.")


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if hasattr(request.user, "steam_account"):
            sync_steam_account(request.user, request.user.steam_account.steam_id)
        return ok(
            {
                "user": UserSerializer(request.user, context={"request": request}).data,
                "steam": UserSteamAccountSerializer(getattr(request.user, "steam_account", None)).data
                if hasattr(request.user, "steam_account")
                else None,
                "owned_games": UserGameSerializer(request.user.owned_games.select_related("game").all(), many=True).data,
            }
        )


class OwnedGameView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UserGameCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item, _ = UserGame.objects.update_or_create(
            user=request.user,
            game_id=serializer.validated_data["game_id"],
            defaults={
                "playtime_minutes": serializer.validated_data.get("playtime_minutes", 0),
                "source": "manual",
            },
        )
        return ok(UserGameSerializer(item).data, "내 게임에 추가했습니다.", 201)


class OwnedGameDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        request.user.owned_games.filter(pk=pk, source="manual").delete()
        return ok(None, "내 게임에서 삭제했습니다.")


class SteamConnectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SteamConnectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        steam_id = steam_service.resolve_steam_id(serializer.validated_data["steam_id_or_url"])
        account, _ = UserSteamAccount.objects.update_or_create(
            user=request.user,
            defaults={
                "steam_id": steam_id,
                "profile_url": f"https://steamcommunity.com/profiles/{steam_id}",
                "persona_name": request.user.username,
                "library_synced_at": timezone.now(),
            },
        )
        sync_steam_account(request.user, steam_id)
        return ok({"steam_id": account.steam_id, "owned_games": UserGameSerializer(request.user.owned_games.all(), many=True).data})


def sync_steam_account(user, steam_id):
    profile = steam_service.fetch_profile(steam_id)
    account, _ = UserSteamAccount.objects.update_or_create(
        user=user,
        defaults={
            "steam_id": steam_id,
            "profile_url": profile["profile_url"],
            "persona_name": profile["persona_name"],
            "avatar_url": profile["avatar_url"],
            "library_synced_at": timezone.now(),
        },
    )
    if profile["persona_name"] and user.username.startswith("steam_"):
        user.username = _unique_username(profile["persona_name"])
        user.save(update_fields=["username"])

    synced_games = []
    for item in steam_service.fetch_library(steam_id):
        game = _upsert_steam_game(item)
        synced_games.append((game, item["playtime_minutes"]))
        UserGame.objects.update_or_create(
            user=user,
            game=game,
            defaults={"playtime_minutes": item["playtime_minutes"]},
        )
    _enrich_top_played_games(synced_games)
    return account


def send_email_verification(request, user):
    verification = EmailVerificationToken.objects.create(
        user=user,
        email=user.email,
        expires_at=timezone.now() + timedelta(hours=24),
    )
    verify_url = request.build_absolute_uri(reverse("email-verify", args=[verification.token]))
    send_mail(
        "Critical Deal 이메일 인증",
        (
            f"{user.username}님, Critical Deal 가입을 환영합니다.\n\n"
            f"아래 링크를 눌러 이메일 인증을 완료해 주세요. 이 링크는 24시간 동안 유효합니다.\n"
            f"{verify_url}\n\n"
            "본인이 가입하지 않았다면 이 메일을 무시해 주세요."
        ),
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def _upsert_steam_game(item):
    game = Game.objects.filter(steam_app_id=item["steam_app_id"]).first()
    if not game:
        game = Game(steam_app_id=item["steam_app_id"])
    game.title = item["title"]
    game.slug = game.slug or _unique_game_slug(item["title"], item["steam_app_id"])
    game.thumbnail = game.thumbnail or item["thumbnail"]
    game.hero_image = game.hero_image or item["thumbnail"]
    game.short_description = game.short_description or "Imported from Steam library."
    game.save()
    return game


def _enrich_top_played_games(synced_games, limit=20):
    from games.services import enrich_steam_metadata

    top_played = [
        game
        for game, _playtime in sorted(synced_games, key=lambda item: item[1], reverse=True)[:limit]
        if game.steam_app_id
    ]
    enrich_steam_metadata(top_played)


def _unique_username(persona_name):
    base = re.sub(r"[^\w.@+-]", "_", persona_name).strip("_")[:120] or "steam_user"
    username = base
    suffix = 1
    while User.objects.filter(username__iexact=username).exists():
        suffix += 1
        username = f"{base}_{suffix}"[:150]
    return username


def _unique_game_slug(title, steam_app_id):
    base = slugify(title) or f"steam-{steam_app_id}"
    slug = base[:220]
    suffix = 1
    while Game.objects.filter(slug=slug).exists():
        suffix += 1
        slug = f"{base[:210]}-{suffix}"
    return slug
