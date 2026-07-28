from __future__ import annotations

import re
from dataclasses import replace

from models import Listing


APPROVED_RETAILERS = {
    "Amazon",
    "Best Buy",
    "Micro Center",
    "Newegg",
}

APPROVED_SELLERS = {
    "Amazon",
    "Amazon.com",
    "Best Buy",
    "Micro Center",
    "Newegg",
}


def normalize_text(value: str) -> str:
    normalized = value.lower()

    normalized = normalized.replace(
        "so-dimm",
        "sodimm",
    )
    normalized = normalized.replace(
        "so dimm",
        "sodimm",
    )
    normalized = normalized.replace(
        "mt/s",
        "mts",
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    )

    return normalized.strip()


def enrich_from_name(listing: Listing) -> Listing:
    text = normalize_text(listing.name)

    memory_type = listing.memory_type
    form_factor = listing.form_factor
    total_capacity = listing.total_capacity_gb
    module_count = listing.module_count
    module_capacity = listing.module_capacity_gb
    speed_mts = listing.speed_mts

    if "ddr5" in text:
        memory_type = "DDR5"

    if any(
        phrase in text
        for phrase in (
            "sodimm",
            "laptop memory",
            "notebook memory",
        )
    ):
        form_factor = "SODIMM"

    if re.search(
        r"\b5600\s*(mhz|mts)?\b",
        text,
    ):
        speed_mts = 5600

    kit_patterns = (
        r"\b2\s*[x×]\s*16\s*gb\b",
        r"\b16\s*gb\s*[x×]\s*2\b",
        r"\b32\s*gb\s*\(\s*2\s*[x×]\s*16\s*gb\s*\)",
    )

    if any(
        re.search(pattern, text)
        for pattern in kit_patterns
    ):
        total_capacity = 32
        module_count = 2
        module_capacity = 16

    return replace(
        listing,
        memory_type=memory_type,
        form_factor=form_factor,
        total_capacity_gb=total_capacity,
        module_count=module_count,
        module_capacity_gb=module_capacity,
        speed_mts=speed_mts,
    )


def matches_requirements(listing: Listing) -> bool:
    enriched = enrich_from_name(listing)

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