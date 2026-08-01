from datetime import datetime, timezone
from decimal import Decimal

import pytest

from models import Listing
from product_matching import (
    enrich_listing,
    normalize_model_number,
    product_match_key,
)


def make_listing(
    name: str,
    *,
    brand: str | None = None,
    model_number: str | None = None,
) -> Listing:
    return Listing(
        listing_id="test:matching",
        retailer="Micro Center",
        seller="Micro Center",
        name=name,
        price=Decimal("99.99"),
        url="https://example.com/product",
        in_stock=True,
        checked_at=datetime.now(timezone.utc),
        brand=brand,
        model_number=model_number,
    )


@pytest.mark.parametrize(
    "name",
    [
        "Crucial 32GB (2 x 16GB) DDR5-5600 SODIMM Laptop Memory Kit",
        "Crucial 32GB 2x16GB DDR5 5600MHz SO-DIMM Memory",
        "Crucial 16GB x 2 PC5-44800 Laptop Memory",
        "Crucial 32GB Kit (2×16GB) DDR5-5600 262-Pin Notebook RAM",
    ],
)
def test_common_titles_are_recognized(name):
    listing = enrich_listing(make_listing(name))

    assert listing.memory_type == "DDR5"
    assert listing.form_factor == "SODIMM"
    assert listing.total_capacity_gb == 32
    assert listing.module_count == 2
    assert listing.module_capacity_gb == 16
    assert listing.speed_mts == 5600


def test_desktop_memory_is_detected():
    listing = enrich_listing(
        make_listing(
            "Crucial 32GB 2x16GB DDR5-5600 "
            "288-Pin Desktop Memory"
        )
    )

    assert listing.form_factor == "DIMM"


def test_model_number_normalization():
    assert (
        normalize_model_number(
            "CT2K16G56C46S5-BLK"
        )
        == "CT2K16G56C46S5BLK"
    )


def test_matching_model_numbers_have_same_key():
    first = make_listing(
        "Crucial Laptop Memory",
        brand="Crucial",
        model_number="CT2K16G56C46S5",
    )

    second = make_listing(
        "Different Product Title",
        brand="Crucial",
        model_number="CT2K16G56C46S5",
    )

    assert (
        product_match_key(first)
        == product_match_key(second)
    )


def test_same_specs_have_same_fallback_key():
    first = make_listing(
        "Crucial 32GB (2 x 16GB) DDR5-5600 SODIMM Laptop Memory Kit",
        brand="Crucial",
    )

    second = make_listing(
        "Crucial 16GB x2 PC5-44800 Notebook Memory",
        brand="Crucial",
    )

    assert (
        product_match_key(first)
        == product_match_key(second)
    )


def test_different_brands_do_not_match():
    crucial = make_listing(
        "32GB (2 x 16GB) DDR5-5600 SODIMM",
        brand="Crucial",
    )

    kingston = make_listing(
        "32GB (2 x 16GB) DDR5-5600 SODIMM",
        brand="Kingston",
    )

    assert (
        product_match_key(crucial)
        != product_match_key(kingston)
    )


def test_different_speed_does_not_match():
    first = make_listing(
        "32GB (2 x 16GB) DDR5-5600 SODIMM",
        brand="Crucial",
    )

    second = make_listing(
        "32GB (2 x 16GB) DDR5-4800 SODIMM",
        brand="Crucial",
    )

    assert (
        product_match_key(first)
        != product_match_key(second)
    )