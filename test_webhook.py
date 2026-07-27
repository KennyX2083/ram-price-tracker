from config import load_settings
from discord_alerts import DiscordNotifier


def main() -> None:
    settings = load_settings()

    notifier = DiscordNotifier(
        settings.discord_webhook_url
    )

    notifier.send_test_message()

    print("Discord webhook test sent successfully.")


if __name__ == "__main__":
    main()