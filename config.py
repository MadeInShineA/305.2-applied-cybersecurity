import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class Config:
    openrouter_api_key: str
    infomaniak_api_key: str
    db_host: str
    db_user: str
    db_password: str
    db_name: str
    mail_imap_host: str
    mail_imap_port: int
    mail_email: str
    mail_password: str
    poll_interval_seconds: int = 300


def load_config() -> Config:
    load_dotenv()
    return Config(
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        infomaniak_api_key=os.getenv("INFOMANIAK_API_KEY", ""),
        db_host=os.getenv("DB_HOST", "localhost"),
        db_user=os.getenv("DB_USER", "root"),
        db_password=os.getenv("DB_PASSWORD", ""),
        db_name=os.getenv("DB_NAME", "email_agent"),
        mail_imap_host=os.getenv("MAIL_IMAP_HOST", "imap.kolabnow.com"),
        mail_imap_port=int(os.getenv("MAIL_IMAP_PORT", "993")),
        mail_email=os.getenv("MAIL_EMAIL", ""),
        mail_password=os.getenv("MAIL_PASSWORD", ""),
        poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "300")),
    )
