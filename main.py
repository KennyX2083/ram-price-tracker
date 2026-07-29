from __future__ import annotations

from alert_rules import AlertEvaluator
from config import Settings, load_settings
from database import Database
from deal_processor import DealProcessor
from discord_alerts import DiscordNotifier
from retailers.base import RetailerClient
from retailers.microcenter import MicroCenterClient


def build_processor(
    settings: Settings,
) -> DealProcessor:

    database = Database(settings.database_path)
    database.initialize()

    notifier = DiscordNotifier(
        settings.discord_webhook_url
    )

    evaluator = AlertEvaluator(
        database=database,
        settings=settings,
    )

    return DealProcessor(
        database=database,
        evaluator=evaluator,
        notifier=notifier,
    )


def run_retailer(
    retailer: RetailerClient,
    processor: DealProcessor,
) -> None:
    try:
        listings = retailer.search()
    except Exception as error:
        print(
            f"Failed to search "
            f"{retailer.__class__.__name__}: {error}"
        )
        return

    print(
        f"Found {len(listings)} listing(s) from "
        f"{retailer.__class__.__name__}."
    )

    for listing in listings:
        try:
            processor.process(listing)
        except Exception as error:
            print(
                f"Failed to process "
                f"{listing.listing_id}: {error}"
            )


def main() -> None:
    settings = load_settings()
    processor = build_processor(settings)

    retailers: list[RetailerClient] = [
        # Retailer clients will be added here.
    ]

    if settings.best_buy_api_key:
        from retailers.best_buy import BestBuyClient

        retailers.append(
            BestBuyClient(
                settings.best_buy_api_key
            )
        )
    else:
        print(
            "Best Buy skipped: "
            "API key is not configured."
        )

    if settings.microcenter_product_urls:
        retailers.append(
            MicroCenterClient(
                settings.microcenter_product_urls
            )
        )
    else:
        print(
            "Microcenter skipped: " \
            "no product URLs are configured."
        )

    if not retailers:
        print(
            "No retailer clients are configured."
        )
        return

    for retailer in retailers:
        run_retailer(
            retailer,
            processor,
        )


if __name__ == "__main__":
    main()