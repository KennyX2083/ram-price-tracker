from __future__ import annotations

from alert_rules import AlertEvaluator
from config import load_settings
from database import Database
from deal_processor import DealProcessor
from discord_alerts import DiscordNotifier
from retailers.base import RetailerClient


def build_processor() -> DealProcessor:
    settings = load_settings()

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
    processor = build_processor()

    retailers: list[RetailerClient] = [
        # Retailer clients will be added here.
    ]

    if not retailers:
        print(
            "RAM Deal Tracker initialized successfully."
        )
        print(
            "No retailer clients are configured yet."
        )
        return

    for retailer in retailers:
        run_retailer(retailer, processor)


if __name__ == "__main__":
    main()