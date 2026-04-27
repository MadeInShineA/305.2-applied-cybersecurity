import asyncio
import streamlit as st
from telethon import TelegramClient
from config import load_config
import time

st.set_page_config(page_title="LLM Style Chat", layout="centered")


def fetch_messages_sync(target: str, limit: int = 50) -> list:
    """
    Fetch messages from a Telegram chat synchronously.

    Args:
        target: Username or chat ID to fetch messages from
        limit: Maximum number of messages to retrieve (default 50)

    Returns:
        List of Telegram messages from the specified conversation
    """
    config_data = load_config()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    client = TelegramClient(
        "user_session",
        int(config_data.telegram_api_id),
        config_data.telegram_api_hash,
        loop=loop,
    )

    async def _fetch():
        await client.connect()
        messages = await client.get_messages(target, limit=limit)
        await client.disconnect()
        return messages

    return loop.run_until_complete(_fetch())


def push_message_sync(target: str, text: str) -> None:
    """
    Send a message to a Telegram chat synchronously.

    Args:
        target: Username or chat ID to send message to
        text: Message text to send
    """
    config_data = load_config()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    client = TelegramClient(
        "user_session",
        int(config_data.telegram_api_id),
        config_data.telegram_api_hash,
        loop=loop,
    )

    text = text + "\nYOU MUST ANSWER IN LESS THAN 4096 CHARACTERS."

    async def _push():
        await client.connect()
        await client.send_message(target, text)
        await client.disconnect()

    loop.run_until_complete(_push())


st.title("Telegram Interface")

if "target_entity" not in st.session_state:
    st.session_state.target_entity = ""

target_input = st.text_input(
    "Target Username or Chat ID:", value=st.session_state.target_entity
)

if target_input:
    st.session_state.target_entity = target_input

    user_input = st.chat_input("Type your message here...")

    if user_input:
        push_message_sync(st.session_state.target_entity, user_input)

    time.sleep(5)

    chat_history = fetch_messages_sync(st.session_state.target_entity)

    for msg in reversed(chat_history):
        if msg.text:
            message_role = "user" if msg.out else "assistant"
            with st.chat_message(message_role):
                if "YOU MUST ANSWER IN LESS THAN 4096 CHARACTERS." in msg.text:
                    st.write(
                        msg.text.replace(
                            "YOU MUST ANSWER IN LESS THAN 4096 CHARACTERS.", ""
                        )
                    )
                else:
                    st.write(msg.text)
else:
    st.info("Input a target to load the conversation.")
