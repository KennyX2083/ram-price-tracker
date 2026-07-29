from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Iterator

from models import Listing


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS listings (
    listing_id TEXT PRIMARY KEY,
    retailer TEXT NOT NULL,
    seller TEXT NOT NULL,
    name TEXT NOT NULL,
    brand TEXT,
    model_number TEXT,
    url TEXT NOT NULL,
    image_url TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id TEXT NOT NULL,
    price_cents INTEGER NOT NULL,
    in_stock INTEGER NOT NULL,
    checked_at TEXT NOT NULL,

    FOREIGN KEY (listing_id)
        REFERENCES listings(listing_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_price_history_listing_time
ON price_history(listing_id, checked_at);

CREATE TABLE IF NOT EXISTS alert_state (
    listing_id TEXT PRIMARY KEY,
    below_price_threshold INTEGER NOT NULL DEFAULT 0,
    below_average_threshold INTEGER NOT NULL DEFAULT 0,
    last_alerted_at TEXT,
    last_alerted_price_cents INTEGER,

    FOREIGN KEY (listing_id)
        REFERENCES listings(listing_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id TEXT NOT NULL,
    price_cents INTEGER NOT NULL,
    average_30d_cents INTEGER,
    reason TEXT NOT NULL,
    alerted_at TEXT NOT NULL,

    FOREIGN KEY (listing_id)
        REFERENCES listings(listing_id)
        ON DELETE CASCADE
);
"""


class Database:
    def __init__(self, path: str) -> None:
        self.path = path

        Path(path).parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row

        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    def register_listing(
        self,
        listing: Listing,
    ) -> None:
        checked_at = listing.checked_at.isoformat()
    
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO listings (
                    listing_id,
                    retailer,
                    seller,
                    name,
                    brand,
                    model_number,
                    url,
                    image_url,
                    first_seen_at,
                    last_seen_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(listing_id) DO UPDATE SET
                    retailer = excluded.retailer,
                    seller = excluded.seller,
                    name = excluded.name,
                    brand = excluded.brand,
                    model_number = excluded.model_number,
                    url = excluded.url,
                    image_url = excluded.image_url,
                    last_seen_at = excluded.last_seen_at
                """,
                (
                    listing.listing_id,
                    listing.retailer,
                    listing.seller,
                    listing.name,
                    listing.brand,
                    listing.model_number,
                    listing.url,
                    listing.image_url,
                    checked_at,
                    checked_at,
                ),
            )

            connection.execute(
                """
                INSERT OR IGNORE INTO alert_state (
                    listing_id
                )
                VALUES (?)
                """,
                (listing.listing_id,),
            )
    
    def save_price_observation(
        self,
        listing: Listing,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO price_history (
                    listing_id,
                    price_cents,
                    in_stock,
                    checked_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    listing.listing_id,
                    decimal_to_cents(listing.price),
                    int(listing.in_stock),
                    listing.checked_at.isoformat(),
                ),
            )

    def save_observation(
        self,
        listing: Listing,
    ) -> None:
        self.register_listing(listing)
        self.save_price_observation(listing)
        
    def get_observation_count(
        self,
        listing_id: str,
    ) -> int:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS observation_count
                FROM price_history
                WHERE listing_id = ?
                """,
                (listing_id,),
            ).fetchone()

        return int(row["observation_count"])

    def get_previous_price(
        self,
        listing_id: str,
    ) -> Decimal | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT price_cents
                FROM price_history
                WHERE listing_id = ?
                ORDER BY checked_at DESC, id DESC
                LIMIT 1 OFFSET 1
                """,
                (listing_id,),
            ).fetchone()

        if row is None:
            return None

        return cents_to_decimal(row["price_cents"])

    def get_30_day_statistics(
        self,
        listing_id: str,
    ) -> tuple[Decimal | None, int, int]:
        cutoff = (
            datetime.now(timezone.utc)
            - timedelta(days=30)
        ).isoformat()

        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    AVG(price_cents) AS average_cents,
                    COUNT(*) AS observation_count,
                    COUNT(DISTINCT DATE(checked_at))
                        AS distinct_days
                FROM price_history
                WHERE listing_id = ?
                  AND checked_at >= ?
                  AND in_stock = 1
                """,
                (listing_id, cutoff),
            ).fetchone()

        if row is None or row["average_cents"] is None:
            return None, 0, 0

        average_cents = int(
            Decimal(str(row["average_cents"])).quantize(
                Decimal("1"),
                rounding=ROUND_HALF_UP,
            )
        )

        return (
            cents_to_decimal(average_cents),
            int(row["observation_count"]),
            int(row["distinct_days"]),
        )

    def get_alert_state(
        self,
        listing_id: str,
    ) -> sqlite3.Row:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM alert_state
                WHERE listing_id = ?
                """,
                (listing_id,),
            ).fetchone()

        if row is None:
            raise LookupError(
                f"No alert state exists for {listing_id}."
            )

        return row

    def update_alert_state(
        self,
        listing_id: str,
        below_price_threshold: bool,
        below_average_threshold: bool,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE alert_state
                SET
                    below_price_threshold = ?,
                    below_average_threshold = ?
                WHERE listing_id = ?
                """,
                (
                    int(below_price_threshold),
                    int(below_average_threshold),
                    listing_id,
                ),
            )

    def record_alert(
        self,
        listing_id: str,
        price: Decimal,
        average_30d: Decimal | None,
        reason: str,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()

        average_cents = None

        if average_30d is not None:
            average_cents = decimal_to_cents(
                average_30d
            )

        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO alert_history (
                    listing_id,
                    price_cents,
                    average_30d_cents,
                    reason,
                    alerted_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    listing_id,
                    decimal_to_cents(price),
                    average_cents,
                    reason,
                    now,
                ),
            )

            connection.execute(
                """
                UPDATE alert_state
                SET
                    last_alerted_at = ?,
                    last_alerted_price_cents = ?
                WHERE listing_id = ?
                """,
                (
                    now,
                    decimal_to_cents(price),
                    listing_id,
                ),
            )

def decimal_to_cents(value: Decimal) -> int:
    return int(
        (value * Decimal("100")).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
    )


def cents_to_decimal(value: int) -> Decimal:
    return (
        Decimal(value) / Decimal("100")
    ).quantize(Decimal("0.01"))