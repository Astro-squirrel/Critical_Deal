from django.conf import settings


def absolute_media_url(url, request=None):
    if not url:
        return ""
    if str(url).startswith(("http://", "https://")):
        return str(url)
    if request:
        return request.build_absolute_uri(url)
    base_url = getattr(settings, "BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
    path = str(url) if str(url).startswith("/") else f"/{url}"
    return f"{base_url}{path}"


def user_avatar_url(user, request=None):
    profile = getattr(user, "profile", None)
    if profile and profile.use_default_avatar:
        return ""
    if profile and profile.avatar:
        return absolute_media_url(profile.avatar.url, request)
    steam_account = getattr(user, "steam_account", None)
    if steam_account and steam_account.avatar_url:
        return steam_account.avatar_url
    return ""
