import os
import re
import time
from datetime import datetime, timedelta, timezone as datetime_timezone
from html import unescape
from xml.etree import ElementTree
from urllib.parse import quote_plus

import requests
from django.utils import timezone


class ItadApiError(RuntimeError):
    pass


class ItadService:
    base_url = "https://api.isthereanydeal.com"

    def __init__(self):
        self.timeout = int(os.getenv("ITAD_TIMEOUT", "20"))
        self._appid_map = None
        self._game_id_by_appid_map = None
        self._shop_map = None

    @property
    def api_key(self):
        return os.getenv("ITAD_API_KEY", "").strip()

    @property
    def country(self):
        return os.getenv("ITAD_COUNTRY", "KR").strip().upper()

    @property
    def steam_shop_id(self):
        return os.getenv("ITAD_STEAM_SHOP_ID", "61").strip()

    @property
    def epic_shop_id(self):
        configured = os.getenv("ITAD_EPIC_SHOP_ID", "").strip()
        if configured:
            return configured
        return self.shop_id_for_name("Epic Game Store") or self.shop_id_for_name("Epic Games Store")

    def _request(self, method, path, params=None, json=None):
        if not self.api_key:
            raise ItadApiError("ITAD_API_KEY is not configured.")
        params = dict(params or {})
        params["key"] = self.api_key
        try:
            response = requests.request(
                method,
                f"{self.base_url}{path}",
                params=params,
                json=json,
                headers={"ITAD-API-Key": self.api_key, "Accept": "application/json"},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise ItadApiError(f"ITAD API request failed: {exc}") from exc
        if response.status_code >= 400:
            raise ItadApiError(f"ITAD API error {response.status_code}: {response.text[:300]}")
        return response.json()

    def search_games(self, query, limit=20):
        data = self._request("GET", "/games/search/v1", params={"title": query, "results": limit})
        return [self._normalize_game(item) for item in data if item.get("type") == "game"]

    def current_deals(self, limit=24, sort="-cut"):
        data = self._request(
            "GET",
            "/deals/v2",
            params={
                "country": self.country,
                "limit": limit,
                "sort": sort,
                "nondeals": "false",
                "shops": self.steam_shop_id,
            },
        )
        items = data.get("list", data if isinstance(data, list) else [])
        games = []
        for item in items:
            if item.get("type") != "game":
                continue
            normalized = self._normalize_deal(item)
            if normalized.get("price") and self._is_steam(normalized["price"]) and normalized["price"]["current_price"] > 0:
                games.append(normalized)
        return games

    def current_free_games(self, limit=12):
        shop_ids = [shop_id for shop_id in [self.steam_shop_id, self.epic_shop_id] if shop_id]
        params = {
            "country": self.country,
            "limit": min(int(limit), 200),
            "sort": "price",
            "nondeals": "false",
        }
        if shop_ids:
            params["shops"] = ",".join(shop_ids)
        data = self._request("GET", "/deals/v2", params=params)
        items = data.get("list", data if isinstance(data, list) else [])
        games = []
        for item in items:
            if item.get("type") != "game":
                continue
            normalized = self._normalize_deal(item)
            price = normalized.get("price")
            if price and price["current_price"] == 0:
                games.append(normalized)
        return games

    def popular_games(self, limit=50):
        data = self._request("GET", "/stats/most-popular/v1", params={"limit": min(int(limit), 500)})
        return [self._normalize_game(item) for item in data if item.get("type") == "game"]

    def game_list(self, limit=10000):
        data = self._request("GET", "/unstable/games/list/v1")
        games = [self._normalize_game(item, resolve_appid=False) for item in data if item.get("id") and item.get("title")]
        return games[:limit]

    def fetch_prices(self, game):
        itad_id = self._game_id(game)
        if not itad_id:
            return []
        prices_by_id = self.fetch_prices_for_ids([itad_id])
        return prices_by_id.get(itad_id, [])

    def fetch_prices_for_ids(self, game_ids):
        ids = [game_id for game_id in game_ids if game_id]
        if not ids:
            return {}
        prices = self._request(
            "POST",
            "/games/prices/v3",
            params={"country": self.country, "deals": "false", "shops": self.steam_shop_id},
            json=ids,
        )
        prices_by_id = {game_id: [] for game_id in ids}
        for item in prices:
            game_id = item.get("id")
            if not game_id:
                continue
            for deal in item.get("deals", []):
                price = self._normalize_price_deal(deal)
                if self._is_steam(price) and price["current_price"] >= 0:
                    prices_by_id.setdefault(game_id, []).append(price)
        return prices_by_id

    def fetch_other_store_prices(self, game, limit=2):
        itad_id = self._game_id(game)
        if not itad_id:
            return []
        prices = self._request(
            "POST",
            "/games/prices/v3",
            params={"country": self.country, "deals": "false"},
            json=[itad_id],
        )
        candidates = []
        seen_stores = set()
        for item in prices:
            for deal in item.get("deals", []):
                price = self._normalize_price_deal(deal)
                store_key = price["store_name"].lower()
                if self._is_steam(price) or store_key in seen_stores:
                    continue
                if price["current_price"] <= 0:
                    continue
                seen_stores.add(store_key)
                candidates.append(price)
        return sorted(candidates, key=lambda item: item["current_price"])[:limit]

    def fetch_history(self, game, since=None):
        itad_id = self._game_id(game)
        if not itad_id:
            return []
        params = {"id": itad_id, "country": self.country, "shops": self.steam_shop_id}
        if since:
            params["since"] = since
        return self._request("GET", "/games/history/v2", params=params)

    def lookup_game(self, title):
        data = self._request("GET", "/games/lookup/v1", params={"title": title})
        if not data.get("found"):
            return None
        return self._normalize_game(data["game"])

    def appid_for_game_id(self, game_id):
        self._ensure_appid_maps()
        return self._appid_map.get(game_id, "")

    def game_id_for_appid(self, app_id):
        self._ensure_appid_maps()
        return self._game_id_by_appid_map.get(str(app_id), "")

    def _ensure_appid_maps(self):
        if self._appid_map is not None and self._game_id_by_appid_map is not None:
            return
        self._appid_map = {}
        self._game_id_by_appid_map = {}
        try:
            data = self._request("GET", "/unstable/games/list/v1")
        except ItadApiError:
            data = []
        for item in data:
            if item.get("id") and item.get("appid"):
                game_id = item["id"]
                app_id = str(item["appid"])
                self._appid_map[game_id] = app_id
                self._game_id_by_appid_map[app_id] = game_id

    def shop_id_for_name(self, name):
        normalized_name = name.lower()
        if self._shop_map is None:
            self._shop_map = {}
            try:
                data = self._request("GET", "/service/shops/map/v1")
            except ItadApiError:
                data = []
            for item in data:
                title = item.get("title") or item.get("name") or ""
                if title:
                    self._shop_map[title.lower()] = str(item.get("id") or "")
        return self._shop_map.get(normalized_name, "")

    def _game_id(self, game):
        if game.itad_plain:
            return game.itad_plain
        if getattr(game, "steam_app_id", ""):
            game_id = self.game_id_for_appid(game.steam_app_id)
            if game_id:
                game.itad_plain = game_id
                game.save(update_fields=["itad_plain"])
                return game.itad_plain
        lookup = self.lookup_game(game.title)
        if not lookup:
            return ""
        game.itad_plain = lookup["itad_id"]
        if not game.thumbnail:
            game.thumbnail = lookup.get("thumbnail", "")
        if not game.hero_image:
            game.hero_image = lookup.get("hero_image", "")
        game.save(update_fields=["itad_plain", "thumbnail", "hero_image"])
        return game.itad_plain

    def _normalize_game(self, item, resolve_appid=True):
        steam_app_id = item.get("appid")
        if not steam_app_id and resolve_appid:
            steam_app_id = self.appid_for_game_id(item["id"])
        return {
            "itad_id": item["id"],
            "slug": item.get("slug") or item["id"],
            "title": item.get("title", "Unknown"),
            "thumbnail": self._asset(item, "banner300", "boxart"),
            "hero_image": self._asset(item, "banner600", "banner400", "banner300"),
            "short_description": "Imported from IsThereAnyDeal.",
            "genres": [],
            "popularity_score": int(item.get("count") or item.get("position") or 0),
            "release_date": item.get("releaseDate") or item.get("release_date") or item.get("released"),
            "steam_app_id": str(steam_app_id or ""),
        }

    def _normalize_deal(self, item):
        game = self._normalize_game(item)
        deal = item.get("deal") or item.get("current") or {}
        game["price"] = self._normalize_price_deal(deal)
        return game

    def _normalize_price_deal(self, deal):
        shop = deal.get("shop") or {}
        price = deal.get("price") or {}
        regular = deal.get("regular") or price
        return {
            "store_name": shop.get("name", "Unknown Store"),
            "store_code": str(shop.get("id") or shop.get("name", "unknown")).lower().replace(" ", "-"),
            "current_price": float(price.get("amount") or 0),
            "original_price": float(regular.get("amount") or price.get("amount") or 0),
            "discount_rate": int(deal.get("cut") or 0),
            "currency": price.get("currency", "USD"),
            "url": deal.get("url", ""),
            "historical_low_price": float(price.get("amount") or 0),
            "historical_low_date": deal.get("timestamp"),
        }

    def _is_steam(self, item):
        return item["store_code"] == self.steam_shop_id or item["store_name"].lower() == "steam"

    def _asset(self, item, *keys):
        assets = item.get("assets") or {}
        for key in keys:
            if assets.get(key):
                return assets[key]
        return ""


class SteamService:
    profile_api_url = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
    owned_games_api_url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
    current_players_url = "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/"
    steamcharts_data_url = "https://steamcharts.com/app/{app_id}/chart-data.json"
    app_details_url = "https://store.steampowered.com/api/appdetails"
    app_page_url = "https://store.steampowered.com/app/{app_id}/"
    app_reviews_url = "https://store.steampowered.com/appreviews/{app_id}"
    store_search_url = "https://store.steampowered.com/api/storesearch/"

    def __init__(self):
        self.timeout = 8
        self._appid_map = None

    @property
    def api_key(self):
        return os.getenv("STEAM_API_KEY", "").strip()

    def resolve_steam_id(self, steam_id_or_url):
        match = re.search(r"(\d{15,20})", steam_id_or_url)
        return match.group(1) if match else steam_id_or_url.strip()

    def fetch_profile(self, steam_id):
        if self.api_key:
            try:
                data = requests.get(
                    self.profile_api_url,
                    params={"key": self.api_key, "steamids": steam_id},
                    timeout=self.timeout,
                )
                if data.status_code < 400:
                    players = data.json().get("response", {}).get("players", [])
                    if players:
                        player = players[0]
                        return {
                            "steam_id": steam_id,
                            "persona_name": player.get("personaname") or f"Steam {steam_id}",
                            "profile_url": player.get("profileurl") or f"https://steamcommunity.com/profiles/{steam_id}",
                            "avatar_url": player.get("avatarfull") or player.get("avatarmedium") or player.get("avatar") or "",
                        }
            except requests.RequestException:
                pass

        return self._fetch_public_xml_profile(steam_id)

    def fetch_library(self, steam_id):
        if not self.api_key:
            return self._fetch_public_xml_library(steam_id)
        try:
            response = requests.get(
                self.owned_games_api_url,
                params={
                    "key": self.api_key,
                    "steamid": steam_id,
                    "include_appinfo": 1,
                    "include_played_free_games": 1,
                    "format": "json",
                },
                timeout=self.timeout,
            )
        except requests.RequestException:
            return []
        if response.status_code >= 400:
            return []
        games = response.json().get("response", {}).get("games", [])
        return [
            {
                "steam_app_id": str(item.get("appid")),
                "title": item.get("name") or f"Steam App {item.get('appid')}",
                "playtime_minutes": int(item.get("playtime_forever") or 0),
                "thumbnail": f"https://cdn.akamai.steamstatic.com/steam/apps/{item.get('appid')}/header.jpg",
            }
            for item in games
            if item.get("appid")
        ]

    def fetch_current_players(self, steam_app_id):
        if not steam_app_id:
            return None
        try:
            response = requests.get(
                self.current_players_url,
                params={"appid": steam_app_id},
                timeout=min(self.timeout, 4),
            )
        except requests.RequestException:
            return None
        if response.status_code >= 400:
            return None
        player_count = response.json().get("response", {}).get("player_count")
        try:
            return int(player_count)
        except (TypeError, ValueError):
            return None

    def fetch_player_history(self, steam_app_id, days=14):
        if not steam_app_id:
            return []
        since = timezone.now() - timedelta(days=days)
        try:
            response = requests.get(
                self.steamcharts_data_url.format(app_id=steam_app_id),
                headers={"Accept": "application/json", "User-Agent": "CriticalDeal/1.0"},
                timeout=self.timeout,
            )
        except requests.RequestException:
            return []
        if response.status_code >= 400:
            return []
        try:
            data = response.json()
        except ValueError:
            return []

        history = []
        for item in data if isinstance(data, list) else []:
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            try:
                timestamp = int(item[0])
                players = int(float(item[1] or 0))
            except (TypeError, ValueError):
                continue
            recorded_at = datetime.fromtimestamp(timestamp / 1000, tz=datetime_timezone.utc)
            if recorded_at < since or players <= 0:
                continue
            history.append(
                {
                    "players": players,
                    "recorded_at": recorded_at,
                    "source": "steamcharts",
                }
            )
        return history

    def _fetch_public_xml_library(self, steam_id):
        try:
            response = requests.get(f"https://steamcommunity.com/profiles/{steam_id}/games?tab=all&xml=1", timeout=self.timeout)
        except requests.RequestException:
            return []
        if response.status_code >= 400:
            return []
        try:
            root = ElementTree.fromstring(response.text)
        except ElementTree.ParseError:
            return []

        games = []
        for item in root.findall(".//game"):
            app_id = item.findtext("appID")
            if not app_id:
                continue
            hours = item.findtext("hoursOnRecord") or "0"
            try:
                playtime_minutes = int(float(hours.replace(",", "")) * 60)
            except ValueError:
                playtime_minutes = 0
            games.append(
                {
                    "steam_app_id": str(app_id),
                    "title": item.findtext("name") or f"Steam App {app_id}",
                    "playtime_minutes": playtime_minutes,
                    "thumbnail": f"https://cdn.akamai.steamstatic.com/steam/apps/{app_id}/header.jpg",
                }
            )
        return games

    def fetch_app_details(self, steam_app_id):
        try:
            response = requests.get(
                self.app_details_url,
                params={"appids": steam_app_id, "cc": "KR", "l": "korean"},
                timeout=self.timeout,
            )
        except requests.RequestException:
            return {}
        if response.status_code >= 400:
            return {}
        item = response.json().get(str(steam_app_id), {})
        if not item.get("success"):
            return {}
        data = item.get("data") or {}
        release_date = data.get("release_date") or {}
        return {
            "title": data.get("name") or "",
            "short_description": data.get("short_description") or "",
            "thumbnail": data.get("header_image") or "",
            "hero_image": data.get("background_raw") or data.get("background") or data.get("header_image") or "",
            "release_date": release_date.get("date") or "",
            "genres": [genre.get("description") for genre in data.get("genres", []) if genre.get("description")],
        }

    def fetch_app_tags(self, steam_app_id, limit=20):
        try:
            response = requests.get(
                self.app_page_url.format(app_id=steam_app_id),
                params={"cc": "KR", "l": "korean"},
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Cookie": "birthtime=568022401; lastagecheckage=1-January-1988; wants_mature_content=1",
                },
                timeout=self.timeout,
            )
        except requests.RequestException:
            return None
        if response.status_code >= 400:
            return None

        tags = []
        seen = set()
        matches = re.findall(r'<a[^>]+class="[^"]*\bapp_tag\b[^"]*"[^>]*>(.*?)</a>', response.text, flags=re.IGNORECASE | re.DOTALL)
        for match in matches:
            name = self._clean_app_tag(match)
            normalized = name.casefold()
            if not name or normalized in seen:
                continue
            seen.add(normalized)
            rank = len(tags) + 1
            tags.append({"name": name, "rank": rank, "weight": max(1, limit - rank + 1)})
            if len(tags) >= limit:
                break
        return tags

    def fetch_current_prices(self, steam_app_ids, batch_size=100):
        app_ids = [str(app_id) for app_id in steam_app_ids if app_id]
        prices = {}
        for start in range(0, len(app_ids), batch_size):
            batch = app_ids[start : start + batch_size]
            params = {
                "appids": ",".join(batch),
                "cc": "KR",
                "l": "korean",
                "filters": "price_overview",
            }
            try:
                response = requests.get(self.app_details_url, params=params, timeout=self.timeout)
            except requests.RequestException:
                continue
            if response.status_code == 429:
                time.sleep(2)
                try:
                    response = requests.get(self.app_details_url, params=params, timeout=self.timeout)
                except requests.RequestException:
                    continue
            if response.status_code >= 400:
                continue
            data = response.json() or {}
            for app_id in batch:
                item = data.get(str(app_id)) or {}
                if not item.get("success"):
                    continue
                price = (item.get("data") or {}).get("price_overview") or {}
                if not price:
                    continue
                current_price = self._steam_amount(price.get("final"))
                original_price = self._steam_amount(price.get("initial")) or current_price
                prices[str(app_id)] = {
                    "store_name": "Steam",
                    "store_code": "steam",
                    "current_price": current_price,
                    "original_price": original_price,
                    "discount_rate": int(price.get("discount_percent") or 0),
                    "currency": price.get("currency", "KRW"),
                    "url": f"https://store.steampowered.com/app/{app_id}/",
                }
        return prices

    def fetch_related_products(self, steam_app_id, dlc_limit=12):
        data = self._fetch_appdetails_data(steam_app_id)
        if data is None:
            return {"dlc": [], "bundles": [], "failed": True}
        if not data:
            return {"dlc": [], "bundles": []}
        dlc_ids = [str(app_id) for app_id in (data.get("dlc") or []) if app_id]
        dlc_ids = dlc_ids[:dlc_limit]
        dlc_products, dlc_failed = self._fetch_dlc_products(dlc_ids)
        return {
            "dlc": dlc_products,
            "bundles": [],
            "failed": dlc_failed,
        }

    def _fetch_appdetails_data(self, steam_app_id):
        try:
            response = requests.get(
                self.app_details_url,
                params={"appids": steam_app_id, "cc": "KR", "l": "korean"},
                timeout=self.timeout,
            )
        except requests.RequestException:
            return None
        if response.status_code >= 400:
            return None
        item = response.json().get(str(steam_app_id), {})
        if not item.get("success"):
            return {}
        return item.get("data") or {}

    def _fetch_dlc_products(self, dlc_ids):
        if not dlc_ids:
            return [], False
        items = []
        failed = False
        for app_id in dlc_ids:
            try:
                response = requests.get(
                    self.app_details_url,
                    params={"appids": app_id, "cc": "KR", "l": "korean"},
                    timeout=self.timeout,
                )
            except requests.RequestException:
                failed = True
                continue
            if response.status_code == 429:
                time.sleep(2)
                try:
                    response = requests.get(
                        self.app_details_url,
                        params={"appids": app_id, "cc": "KR", "l": "korean"},
                        timeout=self.timeout,
                    )
                except requests.RequestException:
                    failed = True
                    continue
            if response.status_code >= 400:
                failed = True
                continue
            item = response.json().get(str(app_id), {})
            if not item.get("success"):
                continue
            data = item.get("data") or {}
            price = data.get("price_overview") or {}
            release_date = data.get("release_date") or {}
            items.append(
                {
                    "id": str(app_id),
                    "type": "dlc",
                    "title": data.get("name") or f"Steam App {app_id}",
                    "thumbnail": data.get("header_image") or "",
                    "hero_image": data.get("background_raw") or data.get("background") or data.get("header_image") or "",
                    "short_description": data.get("short_description") or "",
                    "release_date": release_date.get("date") or "",
                    "genres": [genre.get("description") for genre in data.get("genres", []) if genre.get("description")],
                    "current_price": self._steam_amount(price.get("final")) if price else 0,
                    "original_price": self._steam_amount(price.get("initial")) if price else 0,
                    "discount_rate": int(price.get("discount_percent") or 0),
                    "currency": price.get("currency", "KRW") if price else "KRW",
                    "url": f"https://store.steampowered.com/app/{app_id}/",
                    "is_free": bool(data.get("is_free")),
                }
            )
        return sorted(items, key=lambda item: (item["current_price"] <= 0 and not item["is_free"], item["current_price"], item["title"])), failed

    def _package_products(self, data):
        packages = []
        seen = set()
        for group in data.get("package_groups", []) or []:
            for sub in group.get("subs", []) or []:
                package_id = str(sub.get("packageid") or "")
                if not package_id or package_id in seen:
                    continue
                seen.add(package_id)
                current = self._steam_amount(sub.get("price_in_cents_with_discount"))
                discount = int(sub.get("discount_pct") or 0)
                original = int(round(current / (1 - discount / 100))) if current and discount < 100 and discount > 0 else current
                packages.append(
                    {
                        "id": package_id,
                        "type": "bundle",
                        "title": self._clean_package_title(sub.get("option_text") or sub.get("option_description") or "Steam 패키지"),
                        "thumbnail": data.get("header_image") or "",
                        "current_price": current,
                        "original_price": original,
                        "discount_rate": discount,
                        "currency": "KRW",
                        "url": f"https://store.steampowered.com/sub/{package_id}/",
                        "included_count": int(sub.get("appids", "").count(",") + 1) if sub.get("appids") else None,
                    }
                )
        return sorted(packages, key=lambda item: (item["current_price"], item["title"]))[:8]

    def _steam_amount(self, value):
        amount = int(value or 0)
        return amount // 100

    def _clean_app_tag(self, value):
        tag = re.sub(r"<[^>]+>", "", value or "")
        tag = unescape(tag)
        tag = re.sub(r"\s+", " ", tag).strip()
        return tag[:80]

    def _clean_package_title(self, value):
        title = re.sub(r"<[^>]+>", "", value).strip()
        title = re.sub(r"\s*-\s*(?:₩|&#8361;|KRW)\s*[\d,]+.*$", "", title, flags=re.IGNORECASE)
        return title or "Steam 번들"

    def fetch_review_summary(self, steam_app_id):
        try:
            response = requests.get(
                self.app_reviews_url.format(app_id=steam_app_id),
                params={"json": 1, "filter": "summary", "language": "all", "purchase_type": "all"},
                timeout=self.timeout,
            )
        except requests.RequestException:
            return {}
        if response.status_code >= 400:
            return {}
        summary = response.json().get("query_summary") or {}
        total_reviews = int(summary.get("total_reviews") or 0)
        total_positive = int(summary.get("total_positive") or 0)
        score = round((total_positive / total_reviews) * 100) if total_reviews else 0
        return {
            "steam_review_score": score,
            "steam_review_count": total_reviews,
        }

    def find_app_id(self, title):
        search_title = self._clean_search_title(title)
        try:
            response = requests.get(
                self.store_search_url,
                params={"term": search_title, "cc": "KR", "l": "korean"},
                timeout=self.timeout,
            )
        except requests.RequestException:
            return ""
        if response.status_code >= 400:
            return ""
        items = response.json().get("items", [])
        if not items:
            return ""
        normalized_title = re.sub(r"\W+", "", search_title).lower()
        for item in items:
            item_title = re.sub(r"\W+", "", item.get("name", "")).lower()
            if item_title == normalized_title:
                return str(item.get("id") or "")
        return str(items[0].get("id") or "")

    def _clean_search_title(self, title):
        cleaned = re.sub(r"[^\x20-\x7E가-힣]+", " ", title or "")
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _fetch_public_xml_profile(self, steam_id):
        profile_url = f"https://steamcommunity.com/profiles/{steam_id}"
        try:
            response = requests.get(f"{profile_url}?xml=1", timeout=self.timeout)
        except requests.RequestException:
            return {
                "steam_id": steam_id,
                "persona_name": f"Steam {steam_id}",
                "profile_url": profile_url,
                "avatar_url": "",
            }
        if response.status_code >= 400:
            return {
                "steam_id": steam_id,
                "persona_name": f"Steam {steam_id}",
                "profile_url": profile_url,
                "avatar_url": "",
            }
        try:
            root = ElementTree.fromstring(response.text)
        except ElementTree.ParseError:
            return {
                "steam_id": steam_id,
                "persona_name": f"Steam {steam_id}",
                "profile_url": profile_url,
                "avatar_url": "",
            }
        return {
            "steam_id": steam_id,
            "persona_name": root.findtext("steamID") or f"Steam {steam_id}",
            "profile_url": root.findtext("profileURL") or profile_url,
            "avatar_url": root.findtext("avatarFull") or root.findtext("avatarMedium") or root.findtext("avatarIcon") or "",
        }


class EpicService:
    def free_games(self, items=None):
        games = []
        for item in items if items is not None else itad_service.current_free_games(limit=24):
            price = item.get("price") or {}
            source = price.get("store_name") or "Unknown Store"
            games.append(
                {
                    "title": item["title"],
                    "thumbnail": item.get("thumbnail") or item.get("hero_image") or "",
                    "claim_url": _claim_url(source, item, price),
                    "starts_at": timezone.now(),
                    "ends_at": None,
                    "source": _display_store_name(source),
                }
            )
        return games


def _store_url(source):
    source = source.lower()
    if "steam" in source:
        return "https://store.steampowered.com/"
    if "epic" in source:
        return "https://store.epicgames.com/"
    return "https://isthereanydeal.com/"


def _claim_url(source, item, price):
    source_key = source.lower()
    steam_app_id = item.get("steam_app_id")
    if "steam" in source_key and steam_app_id:
        return f"https://store.steampowered.com/app/{steam_app_id}/"
    if "epic" in source_key:
        return f"https://store.epicgames.com/browse?q={quote_plus(item['title'])}&sortBy=relevancy&sortDir=DESC&count=40"
    url = price.get("url") or ""
    if url and "isthereanydeal.com" not in url.lower():
        return url
    return _store_url(source)


def _display_store_name(source):
    if source == "Epic Game Store":
        return "Epic Games"
    return source


steam_service = SteamService()
itad_service = ItadService()
epic_service = EpicService()
