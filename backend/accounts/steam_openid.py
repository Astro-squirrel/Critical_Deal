import secrets
from urllib.parse import urlencode

import requests
from django.conf import settings


STEAM_OPENID_URL = "https://steamcommunity.com/openid/login"
STEAM_IDENTIFIER_SELECT = "http://specs.openid.net/auth/2.0/identifier_select"


class SteamOpenIdError(RuntimeError):
    pass


def frontend_url(path="/"):
    base_url = getattr(settings, "FRONTEND_URL", "http://127.0.0.1:5173").rstrip("/")
    return f"{base_url}{path}"


def build_steam_login_url(request):
    state = secrets.token_urlsafe(24)
    request.session["steam_openid_state"] = state
    return_to = request.build_absolute_uri(f"/api/accounts/steam/login/callback/?state={state}")
    realm = request.build_absolute_uri("/").rstrip("/")
    params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.mode": "checkid_setup",
        "openid.return_to": return_to,
        "openid.realm": realm,
        "openid.identity": STEAM_IDENTIFIER_SELECT,
        "openid.claimed_id": STEAM_IDENTIFIER_SELECT,
    }
    return f"{STEAM_OPENID_URL}?{urlencode(params)}"


def verify_steam_callback(request):
    expected_state = request.session.pop("steam_openid_state", "")
    if not expected_state or request.GET.get("state") != expected_state:
        raise SteamOpenIdError("Steam 로그인 요청이 만료되었습니다.")

    claimed_id = request.GET.get("openid.claimed_id", "")
    if "/openid/id/" not in claimed_id:
        raise SteamOpenIdError("Steam 계정 정보를 확인할 수 없습니다.")

    payload = request.GET.copy()
    payload["openid.mode"] = "check_authentication"
    response = requests.post(STEAM_OPENID_URL, data=payload, timeout=8)
    if response.status_code >= 400 or "is_valid:true" not in response.text:
        raise SteamOpenIdError("Steam 인증 검증에 실패했습니다.")

    return claimed_id.rstrip("/").split("/")[-1]
