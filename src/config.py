import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Config:
    """Configuration dataclass containing all API keys and settings."""

    openrouter_api_key: str
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
    poll_interval_seconds: int = 300


def load_config() -> Config:
    """Load configuration from environment variables."""
    load_dotenv()
    return Config(
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
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
