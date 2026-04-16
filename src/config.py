"""
Configuration module for the email agent application.

This module defines the Config dataclass which holds all API keys, credentials,
and settings required by various components of the application. Configuration
values are loaded from environment variables using python-dotenv.
"""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


@dataclass
class Config:
    """
    Configuration dataclass containing all API keys and settings.

    This dataclass serves as the central configuration container for the entire
    email agent application. It encapsulates credentials for various services
    including OpenRouter (LLM), Infomaniak kDrive, MySQL database, and email
    via SMTP/IMAP protocols.

    Attributes:
        openrouter_api_key: API key for OpenRouter service (used for LLM calls).
        openrouter_model: Model identifier for OpenRouter (default: nvidia/nemotron-3-nano-30b-a3b).
        infomaniak_api_key: API key for Infomaniak services (kDrive, mail).
        kdrive_id: Unique identifier for the Infomaniak kDrive instance.
        kdrive_verified_directory_id: Directory ID for storing verified CVs in kDrive.
        kdrive_not_verified_directory_id: Directory ID for storing non-verified CVs in kDrive.
        kdrive_job_offers_directory_id: Directory ID containing job offers in kDrive.
        db_host: MySQL database host address.
        db_user: MySQL database username.
        db_password: MySQL database password.
        db_name: MySQL database name (default: email_agent).
        mail_smtp_host: SMTP server hostname for sending emails.
        mail_smtp_port: SMTP server port number.
        mail_imap_host: IMAP server hostname for receiving emails.
        mail_imap_port: IMAP server port number.
        mail_email: Email address used for sending/receiving.
        mail_password: Password for the email account.
        poll_interval_seconds: Interval in seconds between email polling cycles (default: 300).

    openrouter_api_key: str
    openrouter_model: str
    infomaniak_api_key: str
    kdrive_id: str
    kdrive_verified_directory_id: str
    kdrive_not_verified_directory_id: str
    kdrive_job_offers_directory_id: str
    db_host: str
    db_user: str
    db_password: str
    db_name: str
    mail_smtp_host: str
    mail_smtp_port: int
    mail_imap_host: str
    mail_imap_port: str
    mail_email: str
    mail_password: str
    poll_interval_seconds: Interval in seconds between email polling cycles (default: 300).

    Example:
        >>> config = load_config()
        >>> print(config.openrouter_model)
        nvidia/nemotron-3-nano-30b-a3b
    """

    openrouter_api_key: str
    openrouter_model: str
    infomaniak_api_key: str
    kdrive_id: str
    kdrive_verified_directory_id: str
    kdrive_not_verified_directory_id: str
    kdrive_job_offers_directory_id: str
    db_host: str
    db_user: str
    db_password: str
    db_name: str
    mail_smtp_host: str
    mail_smtp_port: int
    mail_imap_host: str
    mail_imap_port: int
    mail_email: str
    mail_password: str
    poll_interval_seconds: int = 300


def load_config() -> Config:
    """
    Load configuration from environment variables.

    This function reads environment variables using python-dotenv and constructs
    a Config instance with all required settings. Default values are provided
    for certain settings (e.g., openrouter_model, poll_interval_seconds) to ensure
    the application can run with minimal configuration.

    Returns:
        Config: A populated Config instance with all settings from environment variables.

    Raises:
        AttributeError: If required environment variables are missing and accessed.

    Note:
        The function requires a .env file in the project root with appropriate
        environment variables defined. See the project README for required variables.

    Example:
        >>> config = load_config()
        >>> config.openrouter_api_key
        'sk-...'
    """
    load_dotenv()
    return Config(
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        openrouter_model=os.getenv(
            "OPENROUTER_MODEL", "nvidia/nemotron-3-nano-30b-a3b"
        ),
        infomaniak_api_key=os.getenv("INFOMANIAK_API_KEY", ""),
        kdrive_id=os.getenv("KDRIVE_ID"),
        kdrive_verified_directory_id=os.getenv("KDRIVE_VERIFIED_CV_DIRECTORY_ID"),
        kdrive_not_verified_directory_id=os.getenv(
            "KDRIVE_NOT_VERIFIED_CV_DIRECTORY_ID"
        ),
        kdrive_job_offers_directory_id=os.getenv("KDRIVE_JOB_OFFERS_DIRECTORY_ID"),
        db_host=os.getenv("DB_HOST", "localhost"),
        db_user=os.getenv("DB_USER", "root"),
        db_password=os.getenv("DB_PASSWORD", ""),
        db_name=os.getenv("DB_NAME", "email_agent"),
        mail_smtp_host=os.getenv("MAIL_SMTP_HOST"),
        mail_smtp_port=int(os.getenv("MAIL_SMTP_PORT")),
        mail_imap_host=os.getenv("MAIL_IMAP_HOST"),
        mail_imap_port=int(os.getenv("MAIL_IMAP_PORT")),
        mail_email=os.getenv("MAIL_EMAIL", ""),
        mail_password=os.getenv("MAIL_PASSWORD", ""),
        poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "300")),
    )
