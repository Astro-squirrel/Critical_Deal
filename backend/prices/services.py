from datetime import datetime, timedelta, timezone as datetime_timezone
from decimal import Decimal

from django.conf import settings
from django.utils import timezone

from external_apis.services import epic_service, itad_service, steam_service
from .models import DiscountEvent, EpicFreeGame, Price, PriceHistory, Store


def get_or_create_store(code, name):
    code = code or "unknown"
    name = name or "Unknown Store"
    store = Store.objects.filter(code=code).first() or Store.objects.filter(name=name).first()
    if store:
        changed = False
        if store.code != code and store.code == "unknown":
            store.code = code
            changed = True
        if store.name != name and store.name == "Unknown Store":
            store.name = name
            changed = True
        if changed:
            store.save(update_fields=["code", "name"])
        return store
    return Store.objects.create(code=code, name=name)


def apply_itad_price(game, item):
    if item["store_name"].lower() != "steam" or Decimal(str(item["current_price"] or 0)) < 0:
        return None
    store = get_or_create_store(item["store_code"], item["store_name"])
    historical_low_date = _parse_date(item.get("historical_low_date"))
    price, _ = Price.objects.update_or_create(
        game=game,
        store=store,
        defaults={
            "current_price": Decimal(str(item["current_price"] or 0)),
            "original_price": Decimal(str(item["original_price"] or item["current_price"] or 0)),
            "discount_rate": item.get("discount_rate", 0),
            "currency": item.get("currency", "USD"),
            "url": item.get("url", ""),
            "historical_low_price": Decimal(str(item["historical_low_price"] or item["current_price"] or 0)),
            "historical_low_date": historical_low_date,
        },
    )
    record_price_snapshot(price)
    sync_discount_event(price)
    update_steam_historical_low(game)
    return price


def apply_steam_price(game, item):
    # Steam appdetails is fallback current-price data only; ITAD owns price history and discount events.
    if game.itad_plain:
        return None

    store = get_or_create_store("steam", "Steam")
    current_price = Decimal(str(item["current_price"] or 0))
    original_price = Decimal(str(item.get("original_price") or item["current_price"] or 0))
    discount_rate = int(item.get("discount_rate") or 0)
    price = Price.objects.filter(game=game, store=store).first()
    if price:
        price.current_price = current_price
        price.original_price = original_price
        price.discount_rate = discount_rate
        price.currency = item.get("currency", "KRW")
        price.url = item.get("url", "")
        price.save(update_fields=["current_price", "original_price", "discount_rate", "currency", "url", "updated_at"])
    else:
        price = Price.objects.create(
            game=game,
            store=store,
            current_price=current_price,
            original_price=original_price,
            discount_rate=discount_rate,
            currency=item.get("currency", "KRW"),
            url=item.get("url", ""),
            historical_low_price=Decimal("0"),
            historical_low_date=None,
        )
    return price


def record_price_snapshot(price, recorded_at=None):
    recorded_at = recorded_at or timezone.localdate()
    PriceHistory.objects.update_or_create(
        game=price.game,
        store=price.store,
        recorded_at=recorded_at,
        defaults={
            "price": price.current_price,
            "discount_rate": price.discount_rate,
        },
    )


def sync_discount_event(price, recorded_at=None):
    recorded_at = recorded_at or timezone.localdate()
    open_event = (
        DiscountEvent.objects.filter(game=price.game, store=price.store, ended_at__isnull=True)
        .order_by("-started_at")
        .first()
    )
    if price.discount_rate <= 0:
        if open_event:
            open_event.ended_at = recorded_at
            open_event.save(update_fields=["ended_at"])
        return None

    if open_event:
        changed_fields = []
        if price.discount_rate > open_event.discount_rate:
            open_event.discount_rate = price.discount_rate
            changed_fields.append("discount_rate")
        if price.current_price < open_event.low_price:
            open_event.low_price = price.current_price
            changed_fields.append("low_price")
        if changed_fields:
            open_event.save(update_fields=changed_fields)
        return open_event

    return DiscountEvent.objects.create(
        game=price.game,
        store=price.store,
        started_at=recorded_at,
        discount_rate=price.discount_rate,
        low_price=price.current_price,
    )


def sync_prices_for_game(game, force=False, history_days=730, include_history=True):
    newest = game.prices.order_by("-updated_at").first()
    if newest and not force:
        age = timezone.now() - newest.updated_at
        if age.total_seconds() < settings.CACHE_TTL_SECONDS:
            if include_history:
                sync_history_for_game(game, days=history_days)
            return list(game.prices.select_related("store"))

    for item in itad_service.fetch_prices(game):
        apply_itad_price(game, item)
    if include_history:
        sync_history_for_game(game, days=history_days)
    return list(game.prices.select_related("store"))


def sync_prices_for_games(games, batch_size=200):
    games = [game for game in games if game.itad_plain]
    synced = []
    for start in range(0, len(games), batch_size):
        batch = games[start : start + batch_size]
        prices_by_id = itad_service.fetch_prices_for_ids([game.itad_plain for game in batch])
        for game in batch:
            prices = prices_by_id.get(game.itad_plain, [])
            for item in prices:
                apply_itad_price(game, item)
            if prices:
                synced.append(game)
    return synced


def sync_current_steam_prices(games, batch_size=100):
    games = [game for game in games if game.steam_app_id]
    fallback_games = []
    protected_itad = 0
    for game in games:
        if game.itad_plain:
            protected_itad += 1
        else:
            fallback_games.append(game)

    prices_by_app_id = steam_service.fetch_current_prices([game.steam_app_id for game in fallback_games], batch_size=batch_size)
    result = {
        "checked": len(games),
        "updated": 0,
        "changed": 0,
        "discounted": 0,
        "skipped": 0,
        "protected_itad": protected_itad,
    }
    for game in fallback_games:
        item = prices_by_app_id.get(str(game.steam_app_id))
        if not item:
            result["skipped"] += 1
            continue
        previous = game.prices.select_related("store").filter(store__name__iexact="Steam").first()
        previous_state = None
        if previous:
            previous_state = (
                previous.current_price,
                previous.original_price,
                previous.discount_rate,
                previous.currency,
            )
        price = apply_steam_price(game, item)
        if price is None:
            result["protected_itad"] += 1
            continue
        result["updated"] += 1
        current_state = (price.current_price, price.original_price, price.discount_rate, price.currency)
        if previous_state != current_state:
            result["changed"] += 1
        if price.discount_rate > 0:
            result["discounted"] += 1
    return result


def is_steam_price_cache_stale(max_age_seconds=None):
    max_age_seconds = max_age_seconds or settings.DEAL_CACHE_TTL_SECONDS
    latest_updated_at = (
        Price.objects.filter(store__name__iexact="Steam")
        .order_by("-updated_at")
        .values_list("updated_at", flat=True)
        .first()
    )
    if not latest_updated_at:
        return True
    return (timezone.now() - latest_updated_at).total_seconds() >= max_age_seconds


def is_free_games_cache_stale(max_age_seconds=None):
    max_age_seconds = max_age_seconds or settings.DEAL_CACHE_TTL_SECONDS
    latest_updated_at = (
        EpicFreeGame.objects.order_by("-updated_at")
        .values_list("updated_at", flat=True)
        .first()
    )
    if not latest_updated_at:
        return True
    if EpicFreeGame.objects.filter(claim_url__icontains="isthereanydeal.com").exists():
        return True
    return (timezone.now() - latest_updated_at).total_seconds() >= max_age_seconds


def sync_daily_deals(deals_limit=200, popular_limit=500, pool_limit=0, include_free_games=True):
    from games.models import Game
    from games.services import sync_itad_deals, sync_itad_game_pool, sync_itad_popular

    deal_games = sync_itad_deals(deals_limit)
    popular_games = sync_itad_popular(popular_limit) if popular_limit else []
    pool_games = sync_itad_game_pool(pool_limit) if pool_limit else []
    discounted_games = list(
        Game.objects.filter(prices__store__name__iexact="Steam", prices__discount_rate__gt=0)
        .distinct()
        .order_by("-popularity_score", "title")[:500]
    )
    refreshed_discounted_games = sync_prices_for_games(discounted_games)
    free_games = sync_epic_free_games() if include_free_games else []
    return {
        "deals": len(deal_games),
        "popular": len(popular_games),
        "pool": len(pool_games),
        "refreshed_discounted": len(refreshed_discounted_games),
        "free_games": len(free_games),
    }


def sync_history_for_game(game, days=730):
    start = timezone.now() - timedelta(days=days)
    if game.release_date:
        release_start = datetime.combine(game.release_date, datetime.min.time(), tzinfo=datetime_timezone.utc)
        if release_start > start:
            start = release_start
    since = (
        start
        .astimezone(datetime_timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    for entry in itad_service.fetch_history(game, since=since):
        deal = entry.get("deal") or {}
        shop = entry.get("shop") or deal.get("shop") or {}
        if shop.get("name", "").lower() != "steam" and str(shop.get("id", "")) != "61":
            continue
        price = deal.get("price") or {}
        regular = deal.get("regular") or price
        store = get_or_create_store(
            code=str(shop.get("id") or shop.get("name", "unknown")).lower().replace(" ", "-"),
            name=shop.get("name", "Unknown Store"),
        )
        recorded_at = _parse_date(entry.get("timestamp")) or timezone.localdate()
        amount = Decimal(str(price.get("amount", 0)))
        regular_amount = Decimal(str(regular.get("amount", price.get("amount", 0))))
        discount = int(deal.get("cut") or 0)
        if not discount and regular_amount:
            discount = max(0, int((1 - (amount / regular_amount)) * 100))
        PriceHistory.objects.update_or_create(
            game=game,
            store=store,
            recorded_at=recorded_at,
            defaults={"price": amount, "discount_rate": discount},
        )
    update_steam_historical_low(game)


def update_steam_historical_low(game):
    steam_price = game.prices.select_related("store").filter(store__name__iexact="Steam").first()
    if not steam_price:
        return
    low = (
        game.price_history.filter(store__name__iexact="Steam")
        .order_by("price", "recorded_at")
        .values("price", "recorded_at")
        .first()
    )
    if low:
        steam_price.historical_low_price = low["price"]
        steam_price.historical_low_date = low["recorded_at"]
        steam_price.save(update_fields=["historical_low_price", "historical_low_date"])


def sync_epic_free_games():
    raw_items = itad_service.current_free_games(limit=24)
    items = epic_service.free_games(raw_items)
    if items:
        EpicFreeGame.objects.all().delete()
        EpicFreeGame.objects.bulk_create(EpicFreeGame(**item) for item in items)
        from games.services import upsert_itad_game

        for item in raw_items:
            price = item.get("price") or {}
            if price.get("store_name", "").lower() == "steam":
                upsert_itad_game(item, enrich=False)
    return EpicFreeGame.objects.order_by("ends_at", "title")


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None
