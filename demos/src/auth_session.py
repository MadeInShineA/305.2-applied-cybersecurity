import asyncio
from telethon import TelegramClient
from config import load_config


async def setup_session() -> None:
    """
    Initialize and authenticate a Telegram client session.
    
    This function creates a new Telegram client using credentials from config,
    starts the authentication flow (prompting for phone and verification code),
    and establishes a persistent session for future API calls.
    
    The session file (user_session.session) is stored locally and allows
    subsequent runs without re-authentication.
    """
    config_data = load_config()

    client = TelegramClient(
        "user_session", int(config_data.telegram_api_id), config_data.telegram_api_hash
    )

    await client.start()
    print("Session created successfully.")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(setup_session())