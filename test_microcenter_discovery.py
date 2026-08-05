from retailers.microcenter import MicroCenterClient


def main() -> None:
    client = MicroCenterClient(
        headless=False,
    )

    listings = client.search()

    print(
        f"\nMicro Center discovered "
        f"{len(listings)} listing(s)."
    )

    for listing in listings:
        print()
        print(f"Name: {listing.name}")
        print(f"Price: ${listing.price:.2f}")
        print(f"In stock: {listing.in_stock}")
        print(f"Model: {listing.model_number}")
        print(f"URL: {listing.url}")


if __name__ == "__main__":
    main()