from datetime import datetime
from decimal import Decimal

from filters import enrich_from_name, matches_requirements
from models import Listing


def make_listing(
    name: str,
    *,
    retailer: str = "Micro Center",
    seller: str = "Micro Center",
    in_stock: bool = True,
    condition: str = "new",
    memory_type: str | None = None,
    form_factor: str | None = None,
    total_capacity_gb: int | None = None,
    module_count: int | None = None,
    module_capacity_gb: int | None = None,
    speed_mts: int | None = None,
) -> Listing:
    return Listing(
        listing_id="test-listing",
        retailer=retailer,
        seller=seller,
        name=name,
        price=Decimal("99.99"),
        url="https://example.com/product",
        in_stock=in_stock,
        checked_at=datetime.now(),
        condition=condition,
        memory_type=memory_type,
        form_factor=form_factor,
        total_capacity_gb=total_capacity_gb,
        module_count=module_count,
        module_capacity_gb=module_capacity_gb,
        speed_mts=speed_mts,
    )


def test_valid_ram_kit_matches_requirements():
    listing = make_listing(
        "Crucial 32GB (2 x 16GB) DDR5-5600 "
        "SODIMM Laptop Memory Kit"
    )

    assert matches_requirements(listing) is True


def test_ddr4_memory_is_rejected():
    listing = make_listing(
        "Crucial 32GB (2 x 16GB) DDR4-5600 "
        "SODIMM Laptop Memory Kit"
    )

    assert matches_requirements(listing) is False


def test_wrong_speed_is_rejected():
    listing = make_listing(
        "Crucial 32GB (2 x 16GB) DDR5-4800 "
        "SODIMM Laptop Memory Kit"
    )

    assert matches_requirements(listing) is False


def test_desktop_dimm_is_rejected():
    listing = make_listing(
        "Crucial 32GB (2 x 16GB) DDR5-5600 "
        "Desktop DIMM Memory Kit"
    )

    assert matches_requirements(listing) is False


def test_single_32gb_module_is_rejected():
    listing = make_listing(
        "Crucial 32GB DDR5-5600 SODIMM Laptop Memory"
    )

    assert matches_requirements(listing) is False


def test_out_of_stock_listing_is_rejected():
    listing = make_listing(
        "Crucial 32GB (2 x 16GB) DDR5-5600 "
        "SODIMM Laptop Memory Kit",
        in_stock=False,
    )

    assert matches_requirements(listing) is False


def test_used_listing_is_rejected():
    listing = make_listing(
        "Crucial 32GB (2 x 16GB) DDR5-5600 "
        "SODIMM Laptop Memory Kit",
        condition="used",
    )

    assert matches_requirements(listing) is False


def test_unapproved_seller_is_rejected():
    listing = make_listing(
        "Crucial 32GB (2 x 16GB) DDR5-5600 "
        "SODIMM Laptop Memory Kit",
        seller="Random Marketplace Seller",
    )

    assert matches_requirements(listing) is False


def test_so_dimm_spelling_is_normalized():
    listing = make_listing(
        "Crucial 32GB (2 x 16GB) DDR5-5600 "
        "SO-DIMM Laptop Memory Kit"
    )

    enriched = enrich_from_name(listing)

    assert enriched.form_factor == "SODIMM"
    assert matches_requirements(listing) is True


def test_reverse_kit_format_is_recognized():
    listing = make_listing(
        "Crucial 16GB x 2 DDR5-5600 "
        "SODIMM Laptop Memory Kit"
    )

    enriched = enrich_from_name(listing)

    assert enriched.total_capacity_gb == 32
    assert enriched.module_count == 2
    assert enriched.module_capacity_gb == 16
    assert matches_requirements(listing) is True