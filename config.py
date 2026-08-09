from __future__ import annotations
import os
from dataclasses import dataclass
from decimal import Decimal
from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    discord_webhook_url: str
    best_buy_api_key: str | None

    max_price: Decimal
    discount_threshold: Decimal
    alert_cooldown_hours: int

    minimum_history_days: int
    minimum_history_observations: int

    database_path: str

    amazon_credential_id: str
    amazon_credential_secret: str
    amazon_partner_tag: str
    amazon_marketplace: str


def load_settings() -> Settings:
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "").strip()

    if not webhook_url:
        raise RuntimeError(
            "DISCORD_WEBHOOK_URL is missing from the .env file."
        )

    best_buy_api_key = os.getenv("BEST_BUY_API_KEY", "").strip()

    amazon_credential_id = os.getenv(
        "AMAZON_CREDENTIAL_ID",
        "",
    ).strip()

    amazon_credential_secret = os.getenv(
        "AMAZON_CREDENTIAL_SECRET",
        "",
    ).strip()

    amazon_partner_tag = os.getenv(
        "AMAZON_PARTNER_TAG",
        "",
    ).strip()

    amazon_marketplace = os.getenv(
        "AMAZON_MARKETPLACE",
        "www.amazon.com",
    ).strip()

    return Settings(
        discord_webhook_url=webhook_url,
        best_buy_api_key=best_buy_api_key or None,
        max_price=Decimal(os.getenv("MAX_PRICE", "300")),
        discount_threshold=Decimal(
            os.getenv("DISCOUNT_THRESHOLD", "0.20")
        ),
        alert_cooldown_hours=int(
            os.getenv("ALERT_COOLDOWN_HOURS", "24")
        ),
        minimum_history_days=int(
            os.getenv("MIN_HISTORY_DAYS", "7")
        ),
        minimum_history_observations=int(
            os.getenv("MIN_HISTORY_OBSERVATIONS", "20")
        ),
        database_path=os.getenv(
            "DATABASE_PATH",
            "data/ram_prices.db",
        ),
        amazon_credential_id=amazon_credential_id,
        amazon_credential_secret=(
            amazon_credential_secret
        ),
        amazon_partner_tag=amazon_partner_tag,
        amazon_marketplace=amazon_marketplace,
    )