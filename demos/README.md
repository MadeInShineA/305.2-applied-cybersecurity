# Demos Folder

This folder contains demonstration applications for a Telegram-based chat interface with LLM styling capabilities.

## Overview

The demos showcase a Streamlit web application that interfaces with Telegram, allowing users to:
- View chat history from any Telegram conversation
- Send messages directly through the web interface

## Project Structure

```
demos/
├── src/
│   ├── app.py           # Main Streamlit web application
│   ├── auth_session.py  # Script for initial Telegram session authentication
│   └── config.py        # Configuration management using environment variables
├── main.py              # Entry point placeholder
├── .env                 # Environment variables (API credentials)
├── .env.example         # Template for environment variables
└── pyproject.toml       # Project dependencies
```

## Prerequisites

1. **Telegram API Credentials**: Obtain your `TG_API_ID` and `TG_API_HASH` from [my.telegram.org](https://my.telegram.org)
2. **Python**: Version 3.13 or higher
3. **Dependencies**: Install via `uv sync` (you can install `uv` with `https://docs.astral.sh/uv/getting-started/installation/`)

## Setup

1. Copy `.env.example` to `.env` and fill in your Telegram credentials:
   ```
   TG_API_ID=your_api_id
   TG_API_HASH=your_api_hash
   ```

2. Authenticate with Telegram (one-time setup):
   ```bash
   uv run ./src/auth_session.py
   ```
   This will prompt for your phone number and verification code.

3. Run the Streamlit application:
   ```bash
   uv run streamlit run src/app.py
   ```

4. Open your browser to the URL shown (typically `http://localhost:8501`)

## Usage

1. Enter a Telegram username or chat ID in the input field
2. The chat history will automatically load
3. Type a message in the chat input at the bottom to send messages

## Key Components

### app.py
Main Streamlit application that provides a web interface for viewing and sending Telegram messages. Uses async/await with Telethon client, wrapped in synchronous functions for Streamlit compatibility.

### auth_session.py
One-time authentication script that creates a session file (`user_session.session`) for Telegram API access.

### config.py
Configuration loader that reads environment variables and provides typed access to API credentials.

## Dependencies

- **streamlit**: Web UI framework
- **telethon**: Telegram client library
- **python-dotenv**: Environment variable management
- **asyncio**: Asynchronous programming support