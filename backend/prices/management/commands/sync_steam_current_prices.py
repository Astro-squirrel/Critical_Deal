from django.core.management.base import BaseCommand

from games.models import Game
from prices.services import sync_current_steam_prices


class Command(BaseCommand):
    help = "Refresh Steam fallback prices for games that do not have an ITAD price identity."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0, help="Maximum number of games to refresh.")
        parser.add_argument("--batch-size", type=int, default=100, help="Number of Steam app ids per appdetails request.")
        parser.add_argument("--discounted-only", action="store_true", help="Refresh only games currently marked as discounted locally.")

    def handle(self, *args, **options):
        games = Game.objects.exclude(steam_app_id="").order_by("-steam_review_count", "title")
        if options["discounted_only"]:
            games = games.filter(prices__store__name__iexact="Steam", prices__discount_rate__gt=0).distinct()
        if options["limit"]:
            games = games[: options["limit"]]
        result = sync_current_steam_prices(list(games), batch_size=options["batch_size"])
        self.stdout.write(
            self.style.SUCCESS(
                "Steam fallback price sync complete. "
                f"Checked: {result['checked']}, updated: {result['updated']}, changed: {result['changed']}, "
                f"discounted now: {result['discounted']}, skipped: {result['skipped']}, "
                f"ITAD-protected: {result['protected_itad']}."
            )
        )
