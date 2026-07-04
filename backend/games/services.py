import time

from datetime import timedelta

from django.db.models import Max, Min, Q
from django.db.utils import OperationalError
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.text import slugify

from external_apis.services import ItadApiError, itad_service, steam_service
from prices.models import DiscountEvent, Price, PriceHistory
from prices.services import (
    apply_itad_price,
    get_or_create_store,
    sync_history_for_game,
    sync_prices_for_game,
    sync_prices_for_games,
    update_steam_historical_low,
)
from .models import Game, GameTag, Genre, PlayerSnapshot, RelatedProduct, Tag

PLACEHOLDER_DESCRIPTIONS = {"Imported from IsThereAnyDeal.", "Imported from Steam library."}
STEAM_CDN_PREFIX = "https://cdn.akamai.steamstatic.com/steam/apps/"
PLAYER_HISTORY_CACHE_HOURS = 6
PLAYER_HISTORY_RETENTION_DAYS = 30
GAME_SEARCH_ALIASES = [
    {
        "queries": ["dave", "dave the diver", "dave diver", "데이브"],
        "titles": ["데이브 더 다이버", "DAVE THE DIVER"],
        "steam_app_ids": ["1868140"],
    },
]


def upsert_itad_game(item, enrich=True):
    if enrich and (not item.get("thumbnail") or not item.get("hero_image")):
        try:
            lookup = itad_service.lookup_game(item["title"])
            if lookup:
                item = {**item, **{key: value for key, value in lookup.items() if value}}
        except ItadApiError:
            pass
    game = Game.objects.filter(itad_plain=item["itad_id"]).first() or Game.objects.filter(slug=item["slug"]).first()
    if not game:
        game = Game(itad_plain=item["itad_id"])
    game.title = item["title"]
    game.slug = item["slug"]
    if _should_replace_image(game.thumbnail, item.get("thumbnail")):
        game.thumbnail = item.get("thumbnail") or game.thumbnail
    if _should_replace_image(game.hero_image, item.get("hero_image")):
        game.hero_image = item.get("hero_image") or game.hero_image
    game.short_description = item.get("short_description") or game.short_description
    game.popularity_score = item.get("popularity_score", 0)
    game.itad_plain = item["itad_id"]
    if item.get("steam_app_id"):
        game.steam_app_id = item["steam_app_id"]
    release_date = _parse_release_date(item.get("release_date"))
    if release_date:
        game.release_date = release_date
    game.save()
    for name in item.get("genres", []):
        genre, _ = Genre.objects.get_or_create(name=name)
        game.genres.add(genre)
    if item.get("price"):
        apply_itad_price(game, item["price"])
    if enrich and not game.genres.exists():
        enrich_steam_metadata([game])
    return game


def sync_itad_deals(limit=24, sort="-cut"):
    games = []
    for item in itad_service.current_deals(limit=min(int(limit), 200), sort=sort):
        games.append(upsert_itad_game(item, enrich=False))
    return games


def sync_itad_popular(limit=50):
    games = []
    candidates = [upsert_itad_game(item, enrich=False) for item in itad_service.popular_games(limit=limit)]
    priced_games = sync_prices_for_games(candidates)
    priced_ids = {game.id for game in priced_games}
    for game in candidates:
        if game.id in priced_ids:
            games.append(game)
        elif not game.wishlisted_by.exists() and not game.owners.exists():
            game.delete()
    return games


def sync_itad_game_pool(limit=2000):
    candidates = [upsert_itad_game(item, enrich=False) for item in itad_service.game_list(limit=limit)]
    priced_games = sync_prices_for_games(candidates)
    priced_ids = {game.id for game in priced_games}
    for game in candidates:
        if game.id not in priced_ids and not game.wishlisted_by.exists() and not game.owners.exists():
            game.delete()
    return priced_games


def seed_mock_games():
    return sync_itad_deals() + sync_itad_popular(50)


def _parse_release_date(value):
    if not value:
        return None
    parsed_datetime = parse_datetime(value)
    if parsed_datetime:
        return parsed_datetime.date()
    return parse_date(value)


def enrich_missing_steam_genres(limit=20):
    games = Game.objects.filter(genres__isnull=True).order_by("title")[:limit]
    enrich_steam_metadata(games)


def enrich_steam_metadata(games, force=False):
    for game in games:
        if not force and not _needs_steam_metadata(game):
            continue
        if not game.steam_app_id:
            game.steam_app_id = steam_service.find_app_id(game.title)
            if game.steam_app_id:
                game.save(update_fields=["steam_app_id"])
        if not game.steam_app_id:
            continue
        details = steam_service.fetch_app_details(game.steam_app_id)
        if not details:
            continue
        if details.get("title"):
            game.title = details["title"]
        if _should_replace_image(game.thumbnail, details.get("thumbnail")):
            game.thumbnail = details["thumbnail"]
        if _should_replace_image(game.hero_image, details.get("hero_image")):
            game.hero_image = details["hero_image"]
        if details.get("short_description") and (not game.short_description or game.short_description in PLACEHOLDER_DESCRIPTIONS):
            game.short_description = details["short_description"]
        release_date = _parse_release_date(details.get("release_date"))
        if release_date and not game.release_date:
            game.release_date = release_date
        game.save()
        for name in details.get("genres", []):
            genre, _ = Genre.objects.get_or_create(name=name)
            game.genres.add(genre)
        if hasattr(game, "_prefetched_objects_cache"):
            game._prefetched_objects_cache.pop("genres", None)


def sync_steam_tags_for_game(game, refresh=False, limit=20):
    if not game.steam_app_id:
        return None
    if not refresh and game.game_tags.exists():
        return [
            {"name": game_tag.tag.name, "rank": game_tag.rank, "weight": game_tag.weight}
            for game_tag in game.game_tags.select_related("tag").order_by("rank", "tag__name")[:limit]
        ]

    tags = steam_service.fetch_app_tags(game.steam_app_id, limit=limit)
    if tags is None:
        return None

    seen_tag_ids = []
    for item in tags:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        tag, _ = _with_db_lock_retry(lambda: Tag.objects.get_or_create(name=name[:80]))
        _with_db_lock_retry(
            lambda: GameTag.objects.update_or_create(
                game=game,
                tag=tag,
                defaults={
                    "rank": int(item.get("rank") or 0),
                    "weight": int(item.get("weight") or 0),
                    "source": GameTag.STEAM,
                },
            )
        )
        seen_tag_ids.append(tag.id)

    steam_tags = GameTag.objects.filter(game=game, source=GameTag.STEAM)
    if seen_tag_ids:
        _with_db_lock_retry(lambda: steam_tags.exclude(tag_id__in=seen_tag_ids).delete())
    else:
        _with_db_lock_retry(lambda: steam_tags.delete())
    if hasattr(game, "_prefetched_objects_cache"):
        game._prefetched_objects_cache.pop("tags", None)
        game._prefetched_objects_cache.pop("game_tags", None)
    game.tags_updated_at = timezone.now()
    game.save(update_fields=["tags_updated_at"])
    return tags


def _with_db_lock_retry(action, attempts=20):
    for attempt in range(attempts):
        try:
            return action()
        except OperationalError as exc:
            if "database is locked" not in str(exc).lower() or attempt == attempts - 1:
                raise
            time.sleep(0.3 * (attempt + 1))


def enrich_steam_reviews(games):
    updated = 0
    for game in games:
        if not game.steam_app_id:
            game.steam_app_id = steam_service.find_app_id(game.title)
            if game.steam_app_id:
                game.save(update_fields=["steam_app_id"])
        if not game.steam_app_id:
            continue
        summary = steam_service.fetch_review_summary(game.steam_app_id)
        if not summary:
            continue
        game.steam_review_score = summary["steam_review_score"]
        game.steam_review_count = summary["steam_review_count"]
        game.steam_reviews_updated_at = timezone.now()
        game.save(update_fields=["steam_review_score", "steam_review_count", "steam_reviews_updated_at"])
        updated += 1
    return updated


def sync_related_products_for_game(game):
    if not game.steam_app_id:
        return {"dlc": [], "bundles": []}

    products = steam_service.fetch_related_products(game.steam_app_id, dlc_limit=50)
    if products.get("failed"):
        return None
    saved = {"dlc": [], "bundles": []}
    seen = {RelatedProduct.DLC: set(), RelatedProduct.BUNDLE: set()}
    type_map = {"dlc": RelatedProduct.DLC, "bundle": RelatedProduct.BUNDLE}

    for key in ["dlc", "bundles"]:
        for item in products.get(key, []):
            product_type = type_map.get(item.get("type"))
            if not product_type or not item.get("id"):
                continue
            external_id = str(item["id"])
            seen[product_type].add(external_id)
            linked_game = _upsert_related_game(game, item, product_type)
            current_price = normalize_related_price_amount(item.get("current_price"), product_type)
            original_price = normalize_related_price_amount(item.get("original_price"), product_type)
            product, _ = RelatedProduct.objects.update_or_create(
                game=game,
                product_type=product_type,
                external_id=external_id,
                defaults={
                    "linked_game": linked_game,
                    "title": item.get("title") or "Steam 관련 상품",
                    "thumbnail": item.get("thumbnail") or "",
                    "current_price": current_price,
                    "original_price": original_price,
                    "discount_rate": int(item.get("discount_rate") or 0),
                    "currency": item.get("currency") or "KRW",
                    "url": item.get("url") or "",
                    "is_free": bool(item.get("is_free")),
                    "included_count": item.get("included_count"),
                },
            )
            saved[key].append(product)

    for product_type, external_ids in seen.items():
        queryset = RelatedProduct.objects.filter(game=game, product_type=product_type)
        if external_ids:
            stale_products = queryset.exclude(external_id__in=external_ids)
        else:
            stale_products = queryset
        stale_linked_game_ids = list(stale_products.values_list("linked_game_id", flat=True).distinct())
        stale_products.delete()
        _delete_orphan_related_games(stale_linked_game_ids)

    game.related_products_updated_at = timezone.now()
    game.save(update_fields=["related_products_updated_at"])
    return saved


def link_existing_related_product_games(limit=0):
    queryset = (
        RelatedProduct.objects.select_related("game")
        .filter(linked_game__isnull=True)
        .order_by("id")
    )
    if limit:
        queryset = queryset[:limit]

    linked = 0
    for product in queryset:
        linked_game = _upsert_related_game(
            product.game,
            {
                "id": product.external_id,
                "title": product.title,
                "thumbnail": product.thumbnail,
                "current_price": product.current_price,
                "original_price": product.original_price,
                "discount_rate": product.discount_rate,
                "currency": product.currency,
                "url": product.url,
                "is_free": product.is_free,
                "included_count": product.included_count,
            },
            product.product_type,
            fetch_reviews=False,
        )
        if linked_game:
            product.linked_game = linked_game
            product.save(update_fields=["linked_game"])
            linked += 1
    return linked


def prune_package_related_products():
    bundle_products = RelatedProduct.objects.filter(product_type=RelatedProduct.BUNDLE)
    bundle_count = bundle_products.count()
    linked_game_ids = list(
        bundle_products.filter(linked_game__slug__startswith="steam-sub-")
        .values_list("linked_game_id", flat=True)
        .distinct()
    )

    bundle_products.delete()
    orphan_count = _delete_orphan_related_games(linked_game_ids)
    return {"products": bundle_count, "orphan_games": orphan_count}


def _delete_orphan_related_games(game_ids):
    game_ids = [game_id for game_id in game_ids if game_id]
    if not game_ids:
        return 0
    orphan_games = (
        Game.objects.filter(id__in=game_ids)
        .filter(Q(slug__startswith="steam-app-") | Q(slug__startswith="steam-sub-"))
        .filter(related_product_entries__isnull=True, related_products__isnull=True)
        .filter(wishlisted_by__isnull=True, owners__isnull=True)
        .distinct()
    )
    orphan_count = orphan_games.count()
    orphan_games.delete()
    return orphan_count


def normalize_existing_related_product_prices():
    corrected_products = 0
    corrected_prices = 0
    corrected_history = 0
    corrected_events = 0
    affected_game_ids = set()

    products = RelatedProduct.objects.select_related("linked_game").filter(product_type=RelatedProduct.DLC)
    for product in products:
        old_current = int(product.current_price or 0)
        old_original = int(product.original_price or 0)
        current_price = normalize_related_price_amount(old_current, product.product_type)
        original_price = normalize_related_price_amount(old_original, product.product_type)
        changed_fields = []
        if current_price != old_current:
            product.current_price = current_price
            changed_fields.append("current_price")
        if original_price != old_original:
            product.original_price = original_price
            changed_fields.append("original_price")
        if changed_fields:
            product.save(update_fields=changed_fields)
            corrected_products += 1

        if product.linked_game_id:
            affected_game_ids.add(product.linked_game_id)
            price = product.linked_game.prices.filter(store__name__iexact="Steam").first()
            if price:
                price_fields = []
                normalized_current = normalize_related_price_amount(price.current_price, product.product_type)
                normalized_original = normalize_related_price_amount(price.original_price, product.product_type)
                normalized_low = normalize_related_price_amount(price.historical_low_price, product.product_type)
                if normalized_current != int(price.current_price or 0):
                    price.current_price = normalized_current
                    price_fields.append("current_price")
                if normalized_original != int(price.original_price or 0):
                    price.original_price = normalized_original
                    price_fields.append("original_price")
                if normalized_low != int(price.historical_low_price or 0):
                    price.historical_low_price = normalized_low
                    price_fields.append("historical_low_price")
                if price_fields:
                    price.save(update_fields=price_fields)
                    corrected_prices += 1

    history_rows = PriceHistory.objects.filter(game_id__in=affected_game_ids, price__gte=100000)
    for row in history_rows:
        normalized_price = normalize_related_price_amount(row.price, RelatedProduct.DLC)
        if normalized_price != int(row.price or 0):
            row.price = normalized_price
            row.save(update_fields=["price"])
            corrected_history += 1

    event_rows = DiscountEvent.objects.filter(game_id__in=affected_game_ids, low_price__gte=100000)
    for event in event_rows:
        normalized_low = normalize_related_price_amount(event.low_price, RelatedProduct.DLC)
        if normalized_low != int(event.low_price or 0):
            event.low_price = normalized_low
            event.save(update_fields=["low_price"])
            corrected_events += 1

    for game in Game.objects.filter(id__in=affected_game_ids):
        update_steam_historical_low(game)

    return {
        "products": corrected_products,
        "prices": corrected_prices,
        "history": corrected_history,
        "events": corrected_events,
        "games": len(affected_game_ids),
    }


def sync_missing_related_product_histories(limit=0, days=730):
    games = (
        Game.objects.filter(related_product_entries__product_type=RelatedProduct.DLC)
        .distinct()
        .order_by("title")
    )
    candidates = []
    for game in games.iterator():
        if game.price_history.filter(store__name__iexact="Steam").count() <= 1:
            candidates.append(game)
            if limit and len(candidates) >= limit:
                break

    updated = 0
    failed = 0
    for game in candidates:
        before = game.price_history.filter(store__name__iexact="Steam").count()
        try:
            sync_history_for_game(game, days=days)
        except ItadApiError:
            failed += 1
            continue
        after = game.price_history.filter(store__name__iexact="Steam").count()
        if after > before:
            updated += 1
    return {"attempted": len(candidates), "updated": updated, "failed": failed}


def sync_player_history_for_game(game, days=14, force=False):
    if not game.steam_app_id:
        return []

    now = timezone.now()
    latest = game.player_history.order_by("-recorded_at").first()
    since = now - timedelta(days=days)
    if latest and not force and latest.recorded_at >= now - timedelta(hours=PLAYER_HISTORY_CACHE_HOURS):
        return list(game.player_history.filter(recorded_at__gte=since).order_by("recorded_at"))

    entries = steam_service.fetch_player_history(game.steam_app_id, days=days)
    if entries:
        snapshots = []
        for entry in entries:
            snapshot, _ = PlayerSnapshot.objects.update_or_create(
                game=game,
                source=entry.get("source") or PlayerSnapshot.STEAMCHARTS,
                recorded_at=entry["recorded_at"],
                defaults={"players": entry["players"]},
            )
            snapshots.append(snapshot)
        _prune_player_history(game)
        return list(game.player_history.filter(recorded_at__gte=since).order_by("recorded_at"))

    current_players = steam_service.fetch_current_players(game.steam_app_id)
    if current_players is not None:
        PlayerSnapshot.objects.update_or_create(
            game=game,
            source=PlayerSnapshot.STEAM,
            recorded_at=now.replace(second=0, microsecond=0),
            defaults={"players": current_players},
        )
    _prune_player_history(game)
    return list(game.player_history.filter(recorded_at__gte=since).order_by("recorded_at"))


def _prune_player_history(game):
    cutoff = timezone.now() - timedelta(days=PLAYER_HISTORY_RETENTION_DAYS)
    game.player_history.filter(recorded_at__lt=cutoff).delete()
    game.player_history.filter(source=PlayerSnapshot.STEAMCHARTS, players=0).delete()


def _upsert_related_game(parent_game, item, product_type, fetch_reviews=True):
    external_id = str(item.get("id") or "")
    if not external_id:
        return None

    title = item.get("title") or f"Steam App {external_id}"
    steam_app_id = external_id if product_type == RelatedProduct.DLC else ""
    stable_slug = f"steam-app-{external_id}" if product_type == RelatedProduct.DLC else f"steam-sub-{external_id}"
    linked_game = Game.objects.filter(steam_app_id=steam_app_id).first() if steam_app_id else None
    if not linked_game:
        linked_game = Game.objects.filter(slug=stable_slug).first()
    if not linked_game:
        linked_game = Game(slug=_unique_stable_slug(stable_slug))

    linked_game.title = title
    if steam_app_id:
        linked_game.steam_app_id = steam_app_id
    if _should_replace_image(linked_game.thumbnail, item.get("thumbnail")):
        linked_game.thumbnail = item.get("thumbnail") or linked_game.thumbnail
    fallback_hero = item.get("hero_image") or item.get("thumbnail") or parent_game.hero_image or parent_game.thumbnail
    if _should_replace_image(linked_game.hero_image, fallback_hero):
        linked_game.hero_image = fallback_hero

    description = item.get("short_description")
    if not description and product_type == RelatedProduct.BUNDLE:
        description = f"{parent_game.title} 관련 Steam 번들입니다."
    if description and (not linked_game.short_description or linked_game.short_description in PLACEHOLDER_DESCRIPTIONS):
        linked_game.short_description = description

    release_date = _parse_release_date(item.get("release_date"))
    if release_date and not linked_game.release_date:
        linked_game.release_date = release_date
    if not linked_game.popularity_score:
        linked_game.popularity_score = parent_game.popularity_score

    _apply_related_review_summary(linked_game, parent_game, steam_app_id, fetch_reviews=fetch_reviews)
    linked_game.save()
    _apply_related_genres(linked_game, parent_game, item.get("genres") or [])
    _copy_parent_credit_relations(linked_game, parent_game)
    _sync_related_game_price(linked_game, item, product_type)
    return linked_game


def _unique_stable_slug(base):
    base = slugify(base) or "steam-related-product"
    slug = base[:220]
    suffix = 2
    while Game.objects.filter(slug=slug).exists():
        slug = f"{base[:210]}-{suffix}"
        suffix += 1
    return slug


def _apply_related_review_summary(linked_game, parent_game, steam_app_id, fetch_reviews=True):
    summary = steam_service.fetch_review_summary(steam_app_id) if steam_app_id and fetch_reviews else {}
    if summary:
        linked_game.steam_review_score = summary["steam_review_score"]
        linked_game.steam_review_count = summary["steam_review_count"]
        linked_game.steam_reviews_updated_at = timezone.now()
        return
    if not linked_game.steam_review_count and parent_game.steam_review_count:
        linked_game.steam_review_score = parent_game.steam_review_score
        linked_game.steam_review_count = parent_game.steam_review_count
        linked_game.steam_reviews_updated_at = parent_game.steam_reviews_updated_at


def _apply_related_genres(linked_game, parent_game, genre_names):
    if genre_names:
        for name in genre_names:
            genre, _ = Genre.objects.get_or_create(name=name)
            linked_game.genres.add(genre)
    if not linked_game.genres.exists():
        linked_game.genres.set(parent_game.genres.all())


def _copy_parent_credit_relations(linked_game, parent_game):
    if not linked_game.developers.exists():
        linked_game.developers.set(parent_game.developers.all())
    if not linked_game.publishers.exists():
        linked_game.publishers.set(parent_game.publishers.all())


def normalize_related_price_amount(value, product_type):
    amount = int(value or 0)
    if amount <= 0:
        return amount
    threshold = 100000 if product_type == RelatedProduct.DLC else 1000000
    if amount >= threshold and amount % 100 == 0:
        return amount // 100
    return amount


def _sync_related_game_price(linked_game, item, product_type):
    # Related-product Steam prices are fallback display data; ITAD owns history and discount events.
    if linked_game.itad_plain:
        return None

    store = get_or_create_store("steam", "Steam")
    current_price = normalize_related_price_amount(item.get("current_price"), product_type)
    original_price = normalize_related_price_amount(item.get("original_price") or current_price, product_type)
    discount_rate = int(item.get("discount_rate") or 0)
    price = Price.objects.filter(game=linked_game, store=store).first()
    if price:
        price.current_price = current_price
        price.original_price = original_price
        price.discount_rate = discount_rate
        price.currency = item.get("currency") or "KRW"
        price.url = item.get("url") or ""
        price.save(update_fields=["current_price", "original_price", "discount_rate", "currency", "url", "updated_at"])
        return price
    return Price.objects.create(
        game=linked_game,
        store=store,
        current_price=current_price,
        original_price=original_price,
        discount_rate=discount_rate,
        currency=item.get("currency") or "KRW",
        url=item.get("url") or "",
        historical_low_price=0,
        historical_low_date=None,
    )


def _needs_steam_metadata(game):
    return (
        not game.thumbnail
        or not game.hero_image
        or not game.short_description
        or game.short_description in PLACEHOLDER_DESCRIPTIONS
        or not game.release_date
        or not game.genres.exists()
    )


def _should_replace_image(current, candidate):
    if not candidate:
        return False
    if not current:
        return True
    if current == candidate:
        return False
    if current.startswith(STEAM_CDN_PREFIX) and candidate.startswith(STEAM_CDN_PREFIX):
        return False
    if current.startswith(STEAM_CDN_PREFIX) and not candidate.startswith(STEAM_CDN_PREFIX):
        return True
    return False


def ensure_game_image_data(games, limit=12):
    checked = 0
    for game in list(games):
        if checked >= limit:
            break
        if game.thumbnail and game.hero_image and game.steam_app_id:
            continue
        checked += 1
        fields = []
        if not game.steam_app_id and game.itad_plain:
            app_id = itad_service.appid_for_game_id(game.itad_plain)
            if app_id:
                game.steam_app_id = app_id
                fields.append("steam_app_id")
        if not game.steam_app_id:
            try:
                lookup = itad_service.lookup_game(game.title)
            except ItadApiError:
                lookup = None
            if lookup:
                if lookup.get("steam_app_id"):
                    game.steam_app_id = lookup["steam_app_id"]
                    fields.append("steam_app_id")
                if _should_replace_image(game.thumbnail, lookup.get("thumbnail")):
                    game.thumbnail = lookup["thumbnail"]
                    fields.append("thumbnail")
                if _should_replace_image(game.hero_image, lookup.get("hero_image")):
                    game.hero_image = lookup["hero_image"]
                    fields.append("hero_image")
        if not game.steam_app_id:
            app_id = steam_service.find_app_id(game.title)
            if app_id:
                game.steam_app_id = app_id
                fields.append("steam_app_id")
        if game.steam_app_id:
            image_url = f"{STEAM_CDN_PREFIX}{game.steam_app_id}/header.jpg"
            if not game.thumbnail:
                game.thumbnail = image_url
                fields.append("thumbnail")
            if not game.hero_image:
                game.hero_image = image_url
                fields.append("hero_image")
        if fields:
            game.save(update_fields=sorted(set(fields)))


def game_search_filter(query):
    query = (query or "").strip()
    search_filter = Q(title__icontains=query) | Q(genres__name__icontains=query) | Q(tags__name__icontains=query)
    normalized = " ".join(query.lower().split())
    compact = normalized.replace(" ", "")
    for alias in GAME_SEARCH_ALIASES:
        alias_queries = alias.get("queries", [])
        if any(term in normalized or term.replace(" ", "") in compact for term in alias_queries):
            for title in alias.get("titles", []):
                search_filter |= Q(title__icontains=title)
            steam_app_ids = alias.get("steam_app_ids", [])
            if steam_app_ids:
                search_filter |= Q(steam_app_id__in=steam_app_ids)
    return search_filter


def _base_games_and_dlc_filter():
    return Q(related_product_entries__isnull=True) | Q(related_product_entries__product_type=RelatedProduct.DLC)


def search_games(query, include_dlc=False):
    search_filter = game_search_filter(query)
    local = Game.objects.filter(search_filter)
    local = local.filter(_base_games_and_dlc_filter() if include_dlc else Q(related_product_entries__isnull=True)).distinct()
    try:
        for item in itad_service.search_games(query):
            game = upsert_itad_game(item)
            sync_prices_for_game(game, include_history=False)
    except ItadApiError:
        if not local.exists():
            raise
    queryset = Game.objects.filter(search_filter)
    queryset = queryset.filter(_base_games_and_dlc_filter() if include_dlc else Q(related_product_entries__isnull=True))
    return (
        queryset
        .distinct()
        .prefetch_related("genres", "game_tags__tag", "prices__store", "related_product_entries")
    )


def local_game_suggestions(query, include_dlc=False):
    queryset = Game.objects.filter(game_search_filter(query))
    queryset = queryset.filter(_base_games_and_dlc_filter() if include_dlc else Q(related_product_entries__isnull=True))
    return (
        queryset
        .distinct()
        .prefetch_related("genres", "game_tags__tag", "prices__store", "related_product_entries")
        .annotate(
            best_price=Min("prices__current_price", filter=Q(prices__store__name__iexact="Steam")),
            max_discount=Max("prices__discount_rate", filter=Q(prices__store__name__iexact="Steam")),
        )
        .order_by("-steam_review_count", "title")
    )


def game_queryset(include_related_products=True):
    queryset = (
        Game.objects.prefetch_related("genres", "game_tags__tag", "developers", "publishers", "prices__store")
        .annotate(
            best_price=Min("prices__current_price", filter=Q(prices__store__name__iexact="Steam")),
            max_discount=Max("prices__discount_rate", filter=Q(prices__store__name__iexact="Steam")),
        )
        .order_by("-steam_review_count", "title")
    )
    if not include_related_products:
        queryset = queryset.filter(related_product_entries__isnull=True)
    return queryset
