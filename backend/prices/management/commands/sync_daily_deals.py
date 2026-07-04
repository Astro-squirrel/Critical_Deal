from django.core.management.base import BaseCommand

from prices.services import sync_daily_deals


class Command(BaseCommand):
    help = "Refresh current Steam deals, daily price snapshots, discount events, and free games."

    def add_arguments(self, parser):
        parser.add_argument("--deals-limit", type=int, default=200, help="Current Steam deals to import. ITAD caps this at 200.")
        parser.add_argument("--popular-limit", type=int, default=500, help="Popular ITAD games to refresh. Use 0 to skip.")
        parser.add_argument(
            "--pool-limit",
            type=int,
            default=0,
            help="Optional broader ITAD game pool to refresh. Use sparingly because it can make many API calls.",
        )
        parser.add_argument("--skip-free-games", action="store_true", help="Do not refresh the free games cache.")

    def handle(self, *args, **options):
        result = sync_daily_deals(
            deals_limit=options["deals_limit"],
            popular_limit=options["popular_limit"],
            pool_limit=options["pool_limit"],
            include_free_games=not options["skip_free_games"],
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Daily deal sync complete. "
                f"Deals: {result['deals']}, popular: {result['popular']}, pool: {result['pool']}, "
                f"refreshed discounted: {result['refreshed_discounted']}, free games: {result['free_games']}."
            )
        )
