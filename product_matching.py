from __future__ import annotations

import re
from dataclasses import replace

from models import Listing


def normalize_product_text(value: str) -> str:
    text = value.lower()

    text = text.replace("×", "x")
    text = text.replace("so-dimm", "sodimm")
    text = text.replace("so dimm", "sodimm")
    text = text.replace("mt/s", "mts")

    text = re.sub(r"(?<=\d),(?=\d)", "", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def detect_memory_type(text: str) -> str | None:
    if re.search(r"\bddr5\b", text):
        return "DDR5"

    if re.search(r"\bpc5[-\s]?\d+\b", text):
        return "DDR5"

    if re.search(r"\bddr4\b", text):
        return "DDR4"

    return None


def detect_form_factor(text: str) -> str | None:
    sodimm_terms = (
        "sodimm",
        "laptop memory",
        "notebook memory",
        "262-pin",
        "262 pin",
    )

    if any(term in text for term in sodimm_terms):
        return "SODIMM"

    desktop_terms = (
        "udimm",
        "desktop memory",
        "desktop dimm",
        "288-pin",
        "288 pin",
    )

    if any(term in text for term in desktop_terms):
        return "DIMM"

    return None


def detect_speed_mts(text: str) -> int | None:
    if re.search(
        r"\b5600\s*(?:mhz|mts)?\b",
        text,
    ):
        return 5600

    if re.search(
        r"\bpc5[-\s]?44800\b",
        text,
    ):
        return 5600

    other_speed = re.search(
        r"\b(3200|4800|5200|6000|6400)\s*"
        r"(?:mhz|mts)?\b",
        text,
    )

    if other_speed:
        return int(other_speed.group(1))

    return None


def detect_kit_layout(
    text: str,
) -> tuple[int, int, int] | None:
    patterns = (
        r"\b2\s*x\s*16\s*gb\b",
        r"\b16\s*gb\s*x\s*2\b",
        r"\b32\s*gb\s*(?:kit)?\s*"
        r"\(\s*2\s*x\s*16\s*gb\s*\)",
        r"\b32\s*gb\s+2[-\s]?pack\b",
    )

    if any(
        re.search(pattern, text)
        for pattern in patterns
    ):
        return 32, 2, 16

    return None


def enrich_listing(listing: Listing) -> Listing:
    text = normalize_product_text(listing.name)

    memory_type = (
        listing.memory_type
        or detect_memory_type(text)
    )

    form_factor = (
        listing.form_factor
        or detect_form_factor(text)
    )

    speed_mts = (
        listing.speed_mts
        or detect_speed_mts(text)
    )

    total_capacity = listing.total_capacity_gb
    module_count = listing.module_count
    module_capacity = listing.module_capacity_gb

    kit_layout = detect_kit_layout(text)

    if kit_layout is not None:
        (
            detected_total,
            detected_count,
            detected_module_capacity,
        ) = kit_layout

        total_capacity = (
            total_capacity or detected_total
        )

        module_count = (
            module_count or detected_count
        )

        module_capacity = (
            module_capacity
            or detected_module_capacity
        )

    return replace(
        listing,
        memory_type=memory_type,
        form_factor=form_factor,
        total_capacity_gb=total_capacity,
        module_count=module_count,
        module_capacity_gb=module_capacity,
        speed_mts=speed_mts,
    )


def normalize_model_number(
    model_number: str | None,
) -> str | None:
    if not model_number:
        return None

    normalized = re.sub(
        r"[^a-zA-Z0-9]",
        "",
        model_number,
    ).upper()

    return normalized or None


def product_match_key(listing: Listing) -> str:
    enriched = enrich_listing(listing)

    model_number = normalize_model_number(
        enriched.model_number
    )

    if model_number:
        return f"model:{model_number}"

    brand = (
        enriched.brand.strip().lower()
        if enriched.brand
        else "unknown"
    )

    return (
        f"spec:{brand}:"
        f"{enriched.memory_type}:"
        f"{enriched.form_factor}:"
        f"{enriched.total_capacity_gb}:"
        f"{enriched.module_count}x"
        f"{enriched.module_capacity_gb}:"
        f"{enriched.speed_mts}"
    )