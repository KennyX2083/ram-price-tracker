import json
from decimal import Decimal
from pathlib import Path

from filters import matches_requirements
from retailers.amazon import AmazonClient


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "amazon_search.json"
)


def load_fixture() -> dict:
    return json.loads(
        FIXTURE_PATH.read_text(
            encoding="utf-8"
        )
    )


def make_client() -> AmazonClient:
    return AmazonClient(
        credential_id="test-id",
        credential_secret="test-secret",
        partner_tag="test-20",
    )


def test_amazon_client_configuration() -> None:
    configured = make_client()

    unconfigured = AmazonClient(
        credential_id="",
        credential_secret="",
        partner_tag="",
    )

    assert configured.is_configured is True
    assert unconfigured.is_configured is False


def test_parse_amazon_search_response() -> None:
    client = make_client()

    listings = client.parse_search_response(
        load_fixture()
    )

    assert len(listings) == 2

    crucial = listings[0]

    assert crucial.listing_id == (
        "amazon:B0TEST1234"
    )
    assert crucial.retailer == "Amazon"
    assert crucial.seller == "Amazon.com"
    assert crucial.price == Decimal("199.99")

    assert crucial.brand == "Crucial"
    assert crucial.model_number == (
        "CT2K16G56C46S5"
    )

    assert crucial.in_stock is True
    assert crucial.condition == "new"


def test_valid_amazon_ram_matches() -> None:
    client = make_client()

    listings = client.parse_search_response(
        load_fixture()
    )

    assert matches_requirements(
        listings[0]
    ) is True


def test_wrong_amazon_ram_is_rejected() -> None:
    client = make_client()

    listings = client.parse_search_response(
        load_fixture()
    )

    assert matches_requirements(
        listings[1]
    ) is False