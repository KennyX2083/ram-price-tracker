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
    "B&H Photo Video",
    "Best Buy",
    "Micro Center",
    "Newegg",
}


def enrich_from_name(listing: Listing) -> Listing:
    return enrich_listing(listing)

def matches_product_specs(listing: Listing) -> bool:
    """
    Check the RAM specifications without checking
    the retailer or seller.
    """
    enriched = enrich_listing(listing)

    return all((
        enriched.in_stock,
        enriched.condition.lower() == "new",
        enriched.memory_type == "DDR5",
        enriched.form_factor == "SODIMM",
        enriched.total_capacity_gb == 32,
        enriched.module_count == 2,
        enriched.module_capacity_gb == 16,
        enriched.speed_mts == 5600,
    ))

def matches_requirements(listing: Listing) -> bool:
    return all((
        matches_product_specs(listing),
        listing.retailer in APPROVED_RETAILERS,
        listing.seller in APPROVED_SELLERS,
    ))