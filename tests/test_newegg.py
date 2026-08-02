from decimal import Decimal
from pathlib import Path

from bs4 import BeautifulSoup

from filters import matches_requirements
from retailers.newegg import NeweggClient


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "newegg_search.html"
)


def load_fixture() -> BeautifulSoup:
    html = FIXTURE_PATH.read_text(
        encoding="utf-8"
    )

    return BeautifulSoup(
        html,
        "html.parser",
    )


def test_parse_newegg_search_page() -> None:
    client = NeweggClient(
        search_terms=(),
    )

    listings = client.parse_search_page(
        load_fixture()
    )

    assert len(listings) == 3

    crucial = listings[0]

    assert crucial.listing_id == (
        "newegg:N82E16820156316"
    )
    assert crucial.retailer == "Newegg"
    assert crucial.seller == "Newegg"
    assert crucial.price == Decimal("429.00")
    assert crucial.in_stock is True
    assert crucial.condition == "new"

    assert crucial.model_number == (
        "CT2K16G56C46S5"
    )

    assert crucial.image_url == (
        "https://example.com/crucial.jpg"
    )


def test_valid_newegg_kit_matches_filter() -> None:
    client = NeweggClient(
        search_terms=(),
    )

    listings = client.parse_search_page(
        load_fixture()
    )

    assert matches_requirements(
        listings[0]
    ) is True


def test_marketplace_seller_is_rejected() -> None:
    client = NeweggClient(
        search_terms=(),
    )

    listings = client.parse_search_page(
        load_fixture()
    )

    assert listings[1].seller == (
        "Random Marketplace Store"
    )

    assert matches_requirements(
        listings[1]
    ) is False


def test_desktop_memory_is_rejected() -> None:
    client = NeweggClient(
        search_terms=(),
    )

    listings = client.parse_search_page(
        load_fixture()
    )

    assert matches_requirements(
        listings[2]
    ) is False

NEWEGG_PRODUCT_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "newegg_product.html"
)

NEWEGG_MARKETPLACE_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "newegg_marketplace_product.html"
)


def load_html_fixture(
    path: Path,
) -> BeautifulSoup:
    return BeautifulSoup(
        path.read_text(encoding="utf-8"),
        "html.parser",
    )


def test_parse_newegg_as_seller() -> None:
    client = NeweggClient(
        search_terms=(),
    )

    seller = client.parse_product_page_seller(
        load_html_fixture(
            NEWEGG_PRODUCT_FIXTURE
        )
    )

    assert seller == "Newegg"


def test_parse_marketplace_seller() -> None:
    client = NeweggClient(
        search_terms=(),
    )

    seller = client.parse_product_page_seller(
        load_html_fixture(
            NEWEGG_MARKETPLACE_FIXTURE
        )
    )

    assert seller == "Random Memory Store"
    assert seller != "Newegg"