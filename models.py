from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

@dataclass(frozen=True)
class Listing:
    listing_id: str
    retailer: str
    seller: str

    name: str
    price: Decimal
    url: str
    in_stock: bool

    checked_at: datetime

    brand: str | None = None
    model_number: str | None = None
    image_url: str | None = None

    condition: str = "new"

    memory_type: str | None = None
    form_factor: str | None = None
    total_capacity_gb: int | None = None
    module_count: int | None = None
    module_capacity_gb: int | None = None
    speed_mts: int | None = None

@dataclass(frozen=True)
class LatestPrice:
    listing_id: str
    retailer: str
    seller: str
    name: str
    price: Decimal
    url: str
    in_stock: bool
    checked_at: datetime