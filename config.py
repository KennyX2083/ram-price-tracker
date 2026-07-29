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

    microcenter_product_urls: tuple[str, ...]


def load_settings() -> Settings:
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "").strip()

    if not webhook_url:
        raise RuntimeError(
            "DISCORD_WEBHOOK_URL is missing from the .env file."
        )

    best_buy_api_key = os.getenv("BEST_BUY_API_KEY", "").strip()

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
        microcenter_product_urls=tuple(
            url.strip()
            for url in os.getenv(
                "MICROCENTER_PRODUCT_URLS",
                "",
            ).split(",")
            if url.strip()
        ),
    )