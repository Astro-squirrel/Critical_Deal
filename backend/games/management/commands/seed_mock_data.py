from django.core.management.base import BaseCommand

from games.models import Game
from games.services import enrich_missing_steam_genres, sync_itad_deals, sync_itad_game_pool, sync_itad_popular
from prices.models import DiscountEvent, EpicFreeGame, Price, PriceHistory, Store
from prices.services import sync_epic_free_games


class Command(BaseCommand):
    help = "Seed games and prices from IsThereAnyDeal."

    def add_arguments(self, parser):
        parser.add_argument("--keep-existing", action="store_true", help="Do not clear existing game and price data first.")
        parser.add_argument("--popular-limit", type=int, default=500, help="Popular ITAD games to import. ITAD caps this at 500.")
        parser.add_argument("--deals-limit", type=int, default=200, help="Current Steam deals to import. ITAD caps this at 200.")
        parser.add_argument(
            "--pool-limit",
            type=int,
            default=2000,
            help="Active ITAD games to bootstrap from the unstable game list. Use 0 to skip.",
        )
        parser.add_argument(
            "--metadata-limit",
            type=int,
            default=80,
            help="Number of imported games to enrich with Steam metadata after seeding. Use 0 to skip.",
        )

    def handle(self, *args, **options):
        if not options["keep_existing"]:
            DiscountEvent.objects.all().delete()
            PriceHistory.objects.all().delete()
            Price.objects.all().delete()
            EpicFreeGame.objects.all().delete()
            Game.objects.all().delete()
            Store.objects.all().delete()
        deal_games = sync_itad_deals(options["deals_limit"])
        popular_games = sync_itad_popular(options["popular_limit"])
        pool_games = sync_itad_game_pool(options["pool_limit"]) if options["pool_limit"] else []
        sync_epic_free_games()
        Game.objects.filter(prices__isnull=True).delete()
        if options["metadata_limit"]:
            enrich_missing_steam_genres(options["metadata_limit"])
        total = Game.objects.filter(prices__store__name__iexact="Steam").distinct().count()
        self.stdout.write(
            self.style.SUCCESS(
                "IsThereAnyDeal data seeded. "
                f"Deals: {len(deal_games)}, popular: {len(popular_games)}, pool: {len(pool_games)}, total Steam-priced games: {total}."
            )
        )
