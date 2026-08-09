from __future__ import annotations
from alert_rules import AlertEvaluator
from config import Settings, load_settings
from database import Database
from deal_processor import DealProcessor
from discord_alerts import DiscordNotifier
from retailers.base import RetailerClient
from retailers.microcenter import MicroCenterClient
from retailers.newegg import NeweggClient
from retailers.bhphoto import BHPhotoClient
# from retailers.amazon import AmazonClient

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

    retailers.append(
        MicroCenterClient(
            headless=False,
        )
    )

    retailers.append(
        NeweggClient(
            headless=False,
        )
    )

    retailers.append(
        BHPhotoClient(
            headless=False,
        )
    )

    # amazon = AmazonClient(
    #     credential_id=settings.amazon_credential_id,
    #     credential_secret=settings.amazon_credential_secret,
    #     partner_tag=settings.amazon_partner_tag,
    #     marketplace=settings.amazon_marketplace,
    # )

    # if amazon.is_configured:
    #     retailers.append(amazon)
    # else:
    #     print(
    #         "Amazon skipped: "
    #         "credentials are not configured."
    #     )

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