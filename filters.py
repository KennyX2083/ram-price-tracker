from __future__ import annotations
from models import Listing
from product_matching import enrich_listing


APPROVED_RETAILERS = {
    "Amazon",
    "Best Buy",
    "B&H",
    "Micro Center",
    "Newegg",
}

APPROVED_SELLERS = {
    "Amazon",
    "Amazon.com",
    "Best Buy",
    "B&H",
    "B&H Photo Video",
    "Micro Center",
    "Newegg",
}


def enrich_from_name(listing: Listing) -> Listing:
    return enrich_listing(listing)


def matches_requirements(listing: Listing) -> bool:
    enriched = enrich_listing(listing)

    return all((
        enriched.in_stock,
        enriched.condition.lower() == "new",
        enriched.retailer in APPROVED_RETAILERS,
        enriched.seller in APPROVED_SELLERS,
        enriched.memory_type == "DDR5",
        enriched.form_factor == "SODIMM",
        enriched.total_capacity_gb == 32,
        enriched.module_count == 2,
        enriched.module_capacity_gb == 16,
        enriched.speed_mts == 5600,
    ))