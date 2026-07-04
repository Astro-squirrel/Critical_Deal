from django.core.management.base import BaseCommand
from django.db.models import Count, Q
import time

from games.models import Game
from external_apis.services import ItadApiError, itad_service, steam_service
from games.services import (
    PLACEHOLDER_DESCRIPTIONS,
    enrich_steam_metadata,
    enrich_steam_reviews,
    link_existing_related_product_games,
    normalize_existing_related_product_prices,
    prune_package_related_products,
    sync_missing_related_product_histories,
    sync_player_history_for_game,
    sync_related_products_for_game,
    sync_steam_tags_for_game,
)
from prices.services import sync_history_for_game


class Command(BaseCommand):
    help = "Backfill locally stored game metadata without doing work during page loads."

    def add_arguments(self, parser):
        parser.add_argument("--images", action="store_true", help="Store Steam CDN image URLs for games that have a Steam app id.")
        parser.add_argument("--refresh-images", action="store_true", help="Refresh image URLs even when a game already has one.")
        parser.add_argument("--resolve-missing-appids", action="store_true", help="Try to find Steam app ids for games that do not have one.")
        parser.add_argument("--itad-images", action="store_true", help="Try to refresh missing images from IsThereAnyDeal lookup first.")
        parser.add_argument("--image-limit", type=int, default=0, help="Maximum number of games to backfill with Steam image URLs.")
        parser.add_argument("--metadata-limit", type=int, default=0, help="Number of games to enrich from Steam app details.")
        parser.add_argument("--refresh-metadata", action="store_true", help="Refresh Steam metadata even when local fields are already populated.")
        parser.add_argument("--reviews", action="store_true", help="Store Steam review score and review count for games with a Steam app id.")
        parser.add_argument("--refresh-reviews", action="store_true", help="Refresh games that already have Steam review data.")
        parser.add_argument("--review-limit", type=int, default=0, help="Maximum number of games to enrich with Steam reviews.")
        parser.add_argument("--history", action="store_true", help="Store Steam price history for games that have Steam prices.")
        parser.add_argument("--refresh-history", action="store_true", help="Refresh games that already have Steam price history.")
        parser.add_argument("--history-limit", type=int, default=0, help="Maximum number of games to enrich with Steam price history.")
        parser.add_argument("--history-max-existing", type=int, default=None, help="Only refresh games with this many or fewer Steam history rows.")
        parser.add_argument("--history-delay", type=float, default=0.0, help="Delay between ITAD history requests.")
        parser.add_argument("--related-products", action="store_true", help="Store Steam DLC and bundle data for games with a Steam app id.")
        parser.add_argument("--refresh-related-products", action="store_true", help="Refresh games that already have related product data.")
        parser.add_argument("--related-products-existing-only", action="store_true", help="Refresh only games that already have stored related products.")
        parser.add_argument("--related-products-limit", type=int, default=0, help="Maximum number of games to enrich with related products.")
        parser.add_argument("--related-products-delay", type=float, default=1.0, help="Delay between Steam related product requests.")
        parser.add_argument("--link-related-product-games", action="store_true", help="Create internal Game rows for stored DLC and bundles.")
        parser.add_argument("--link-related-product-limit", type=int, default=0, help="Maximum number of stored related products to link.")
        parser.add_argument("--normalize-related-product-prices", action="store_true", help="Fix related DLC prices saved in Steam cent units.")
        parser.add_argument("--prune-package-related-products", action="store_true", help="Remove Steam purchase package options from related products.")
        parser.add_argument("--related-product-history", action="store_true", help="Fetch missing Steam price history for linked DLC detail pages.")
        parser.add_argument("--related-product-history-limit", type=int, default=0, help="Maximum number of linked DLC games to refresh history for.")
        parser.add_argument("--players", action="store_true", help="Store recent Steam player history for games with a Steam app id.")
        parser.add_argument("--refresh-players", action="store_true", help="Refresh player history even when recent cached data exists.")
        parser.add_argument("--player-limit", type=int, default=0, help="Maximum number of games to enrich with player history.")
        parser.add_argument("--player-delay", type=float, default=0.2, help="Delay between player history requests.")
        parser.add_argument("--tags", action="store_true", help="Store Steam user tags for games with a Steam app id.")
        parser.add_argument("--refresh-tags", action="store_true", help="Refresh tags even when a game already has stored tags.")
        parser.add_argument("--tag-limit", type=int, default=20, help="Maximum number of Steam tags to store per game.")
        parser.add_argument("--tag-game-limit", type=int, default=0, help="Maximum number of games to enrich with Steam tags.")
        parser.add_argument("--tag-delay", type=float, default=0.05, help="Delay between Steam tag page requests.")

    def handle(self, *args, **options):
        image_count = (
            self._backfill_steam_images(
                refresh=options["refresh_images"],
                resolve_missing_appids=options["resolve_missing_appids"],
                itad_images=options["itad_images"],
                limit=options["image_limit"],
            )
            if options["images"]
            else 0
        )
        metadata_count = 0
        review_count = 0
        history_count = 0
        history_failed_count = 0
        related_count = 0
        linked_related_count = 0
        normalized_related_count = {}
        pruned_package_count = {}
        related_history_count = {}
        player_count = 0
        player_failed_count = 0
        tag_count = 0
        tag_failed_count = 0

        if options["metadata_limit"]:
            games = Game.objects.filter(steam_app_id__gt="")
            if not options["refresh_metadata"]:
                games = games.filter(
                    Q(genres__isnull=True)
                    | Q(short_description="")
                    | Q(short_description__in=PLACEHOLDER_DESCRIPTIONS)
                    | Q(release_date__isnull=True)
                    | Q(thumbnail="")
                    | Q(hero_image="")
                )
            games = games.distinct().order_by("-popularity_score", "title")[: options["metadata_limit"]]
            games = list(games)
            enrich_steam_metadata(games, force=options["refresh_metadata"])
            metadata_count = len(games)

        if options["reviews"]:
            games = Game.objects.filter(steam_app_id__gt="")
            if not options["refresh_reviews"]:
                games = games.filter(steam_reviews_updated_at__isnull=True)
            games = games.order_by("-popularity_score", "title")
            if options["review_limit"]:
                games = games[: options["review_limit"]]
            review_count = enrich_steam_reviews(list(games))

        if options["history"]:
            games = Game.objects.filter(prices__store__name__iexact="Steam").distinct()
            if options["history_max_existing"] is not None:
                games = games.annotate(
                    steam_history_count=Count(
                        "price_history",
                        filter=Q(price_history__store__name__iexact="Steam"),
                        distinct=True,
                    )
                ).filter(steam_history_count__lte=options["history_max_existing"])
            elif not options["refresh_history"]:
                games = games.filter(price_history__isnull=True)
            games = games.order_by("-popularity_score", "title")
            if options["history_limit"]:
                games = games[: options["history_limit"]]
            games = list(games)
            history_total = len(games)
            for index, game in enumerate(games, 1):
                before = game.price_history.filter(store__name__iexact="Steam").count()
                try:
                    sync_history_for_game(game, days=730)
                except ItadApiError:
                    history_failed_count += 1
                    if options["history_delay"]:
                        time.sleep(options["history_delay"])
                    continue
                after = game.price_history.filter(store__name__iexact="Steam").count()
                if after > before:
                    history_count += 1
                if options["history_delay"]:
                    time.sleep(options["history_delay"])
                if index % 100 == 0 or index == history_total:
                    self.stdout.write(
                        f"History progress: {index}/{history_total}, updated: {history_count}, failures: {history_failed_count}."
                    )

        if options["related_products"]:
            games = Game.objects.filter(steam_app_id__gt="")
            if options["related_products_existing_only"]:
                games = games.filter(related_products__isnull=False)
            elif not options["refresh_related_products"]:
                games = games.filter(related_products_updated_at__isnull=True)
            games = games.distinct().order_by("-popularity_score", "title")
            if options["related_products_limit"]:
                games = games[: options["related_products_limit"]]
            for game in list(games):
                saved = sync_related_products_for_game(game)
                if saved and (saved["dlc"] or saved["bundles"]):
                    related_count += 1
                time.sleep(options["related_products_delay"])

        if options["link_related_product_games"]:
            linked_related_count = link_existing_related_product_games(limit=options["link_related_product_limit"])

        if options["normalize_related_product_prices"]:
            normalized_related_count = normalize_existing_related_product_prices()

        if options["prune_package_related_products"]:
            pruned_package_count = prune_package_related_products()

        if options["related_product_history"]:
            related_history_count = sync_missing_related_product_histories(limit=options["related_product_history_limit"])

        if options["players"]:
            games = Game.objects.filter(steam_app_id__gt="").distinct().order_by("-steam_review_count", "-popularity_score", "title")
            if not options["refresh_players"]:
                games = games.filter(player_history__isnull=True)
            if options["player_limit"]:
                games = games[: options["player_limit"]]
            games = list(games)
            player_total = len(games)
            for index, game in enumerate(games, 1):
                before = game.player_history.count()
                try:
                    sync_player_history_for_game(game, days=14, force=options["refresh_players"])
                except Exception:
                    player_failed_count += 1
                    if options["player_delay"]:
                        time.sleep(options["player_delay"])
                    continue
                after = game.player_history.count()
                if after > before:
                    player_count += 1
                if options["player_delay"]:
                    time.sleep(options["player_delay"])
                if index % 50 == 0 or index == player_total:
                    self.stdout.write(
                        f"Player progress: {index}/{player_total}, updated: {player_count}, failures: {player_failed_count}."
                    )

        if options["tags"]:
            games = Game.objects.filter(steam_app_id__gt="")
            if not options["refresh_tags"]:
                games = games.filter(tags_updated_at__isnull=True)
            games = games.distinct().order_by("-steam_review_count", "-popularity_score", "title")
            if options["tag_game_limit"]:
                games = games[: options["tag_game_limit"]]
            for game in list(games):
                tags = sync_steam_tags_for_game(game, refresh=options["refresh_tags"], limit=options["tag_limit"])
                if tags is None:
                    tag_failed_count += 1
                else:
                    tag_count += 1
                time.sleep(options["tag_delay"])

        self.stdout.write(
            self.style.SUCCESS(
                "Backfill complete. "
                f"Images updated: {image_count}, metadata attempted: {metadata_count}, "
                f"reviews updated: {review_count}, histories updated: {history_count}, history failures: {history_failed_count}, "
                f"related products updated: {related_count}, related products linked: {linked_related_count}, "
                f"related prices normalized: {normalized_related_count}, package products pruned: {pruned_package_count}, "
                f"related histories: {related_history_count}, player histories updated: {player_count}, "
                f"player failures: {player_failed_count}, tags updated: {tag_count}, tag failures: {tag_failed_count}."
            )
        )

    def _backfill_steam_images(self, refresh=False, resolve_missing_appids=False, itad_images=False, limit=0):
        games = Game.objects.all() if resolve_missing_appids else Game.objects.exclude(steam_app_id="")
        if not refresh:
            games = games.filter(Q(thumbnail="") | Q(hero_image=""))
        games = games.order_by("-popularity_score", "title")
        if limit:
            games = games[:limit]
        updated = 0
        for game in games:
            fields = []
            if not game.steam_app_id and resolve_missing_appids and game.itad_plain:
                app_id = itad_service.appid_for_game_id(game.itad_plain)
                if app_id:
                    game.steam_app_id = app_id
                    fields.append("steam_app_id")
            if itad_images and (refresh or not game.thumbnail or not game.hero_image or not game.steam_app_id):
                lookup = self._lookup_itad_images(game)
                if lookup:
                    if lookup.get("steam_app_id") and not game.steam_app_id:
                        game.steam_app_id = lookup["steam_app_id"]
                        fields.append("steam_app_id")
                    if lookup.get("thumbnail") and (refresh or not game.thumbnail):
                        game.thumbnail = lookup["thumbnail"]
                        fields.append("thumbnail")
                    if lookup.get("hero_image") and (refresh or not game.hero_image):
                        game.hero_image = lookup["hero_image"]
                        fields.append("hero_image")
            if not game.steam_app_id and resolve_missing_appids:
                app_id = steam_service.find_app_id(game.title)
                if app_id:
                    game.steam_app_id = app_id
                    fields.append("steam_app_id")
            if not game.steam_app_id:
                if fields:
                    game.save(update_fields=sorted(set(fields)))
                    updated += 1
                continue
            image_url = f"https://cdn.akamai.steamstatic.com/steam/apps/{game.steam_app_id}/header.jpg"
            if refresh or not game.thumbnail:
                game.thumbnail = image_url
                fields.append("thumbnail")
            if refresh or not game.hero_image:
                game.hero_image = image_url
                fields.append("hero_image")
            if fields:
                game.save(update_fields=fields)
                updated += 1
        return updated

    def _lookup_itad_images(self, game):
        try:
            lookup = itad_service.lookup_game(game.title)
        except ItadApiError:
            return None
        if not lookup:
            return None
        if game.itad_plain and lookup.get("itad_id") and lookup["itad_id"] != game.itad_plain:
            normalized_title = _normalize_title(game.title)
            normalized_lookup_title = _normalize_title(lookup.get("title", ""))
            if normalized_title != normalized_lookup_title:
                return None
        return lookup


def _normalize_title(value):
    return "".join(char.lower() for char in value if char.isalnum())
