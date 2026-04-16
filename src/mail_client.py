import datetime
import email
import imaplib
import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.policy import default
from email.utils import parsedate_to_datetime
from io import BytesIO
from typing import List, Optional

import pdfplumber

if __name__ == "__main__":
    import sys
    from pathlib import Path

    project_root = Path(__file__).parent.parent

    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


from src.config import Config


def parse_email_date(date_str: str) -> Optional[str]:
    """Parse email date string to UTC datetime for MySQL."""
    if not date_str:
        return None
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is not None:
            dt = dt.astimezone(datetime.timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


@dataclass
class Email:
    email_id: str
    subject: str
    sender: str
    body: str
    has_pdf_attachment: bool
    attachments: dict
    received_at: Optional[str] = None


class MailClient:
    """Client for IMAP email operations with PDF attachment extraction."""

    def __init__(self, config: Config):
        self.config = config
        self._connection: Optional[imaplib.IMAP4_SSL] = None

    def connect(self) -> None:
        """
        Connects to the IMAP server using mail_imap_host and mail_password.
        """
        try:
            self._connection = imaplib.IMAP4_SSL(
                self.config.mail_imap_host, port=self.config.mail_imap_port
            )
            self._connection.login(self.config.mail_email, self.config.mail_password)
            self._connection.select("INBOX")
        except Exception as e:
            raise Exception(f"Failed to connect to IMAP: {e}")

    def disconnect(self) -> None:
        """
        Closes the IMAP connection safely.
        """
        if self._connection:
            try:
                self._connection.close()
                self._connection.logout()
            except Exception:
                pass
            self._connection = None

    def send_email(
        self,
        to_addresses: List[str],
        subject: str,
        body: str,
        is_html: bool = False,
    ) -> None:
        """
        Sends an email via SMTP using mail_smtp_host and mail_smtp_port.
        """
        msg = MIMEMultipart()
        msg["From"] = self.config.mail_email
        msg["To"] = ", ".join(to_addresses)
        msg["Subject"] = subject

        mime_type = "html" if is_html else "plain"
        msg.attach(MIMEText(body, mime_type))

        try:
            if self.config.mail_smtp_port == 465:
                server = smtplib.SMTP_SSL(
                    self.config.mail_smtp_host, self.config.mail_smtp_port, timeout=30
                )
            else:
                server = smtplib.SMTP(
                    self.config.mail_smtp_host, self.config.mail_smtp_port, timeout=30
                )
                server.starttls()
            with server:
                server.login(self.config.mail_email, self.config.mail_password)
                server.sendmail(self.config.mail_email, to_addresses, msg.as_string())
        except Exception as e:
            raise Exception(f"Failed to send email: {e}")

    def fetch_recent_emails(self, limit: int = 50) -> List[Email]:
        """
        Fetches the most recent emails using IMAP commands.
        """
        if not self._connection:
            self.connect()

        status, messages = self._connection.search(None, "ALL")
        if status != "OK":
            return []

        msg_ids = messages[0].split()
        latest_ids = msg_ids[-limit:]
        latest_ids.reverse()

        emails = []
        for msg_id in latest_ids:
            res, data = self._connection.fetch(msg_id, "(RFC822)")
            if res != "OK":
                continue

            raw_email = data[0][1]
            emails.append(self._parse_raw_email(raw_email))

        return emails

    def _parse_raw_email(self, raw_email: bytes) -> Email:
        """
        Parses raw bytes into a structured Email object.
        """
        msg = email.message_from_bytes(raw_email, policy=default)

        email_id = msg.get("Message-ID", "unknown")

        subject = msg.get("Subject", "No Subject")
        sender = msg.get("From", "Unknown Sender")
        date_str = msg.get("Date", "")
        received_at = parse_email_date(date_str)

        body = ""
        has_pdf = False
        attachments = []

        # Iterate through MIME parts
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = part.get_content_disposition() or ""

            # Extract body (prefer plain text)
            if content_type == "text/plain" and "attachment" not in disposition:
                if not body:  # Only take the first text part
                    body = part.get_content()

            # Detect PDF attachment
            if "attachment" in disposition.lower() or content_type.startswith(
                "application/pdf"
            ):
                filename = part.get_filename()
                if filename and filename.lower().endswith(".pdf"):
                    has_pdf = True
                    # Extract raw bytes
                    pdf_bytes = part.get_payload(decode=True)

                    if pdf_bytes:
                        try:
                            with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
                                # Extract text page by page, preserving layout
                                pages_text = []
                                for page in pdf.pages:
                                    # extract_text() respects columns & reading order
                                    page_text = page.extract_text() or ""
                                    pages_text.append(page_text)

                                full_text = "\n\n".join(pages_text)

                                attachments.append(
                                    {
                                        "filename": filename,
                                        "bytes": pdf_bytes,
                                        "data": full_text,
                                        "metadata": pdf.metadata,
                                    }
                                )
                        except Exception as e:
                            has_pdf = False
        return Email(
            email_id=email_id,
            subject=subject,
            sender=sender,
            body=body[:5000],
            has_pdf_attachment=has_pdf,
            attachments=attachments,
            received_at=received_at,
        )


if __name__ == "__main__":
    from src.config import load_config

    config = load_config()

    mail_client = MailClient(config)

    mail_client.send_email(
        ["loic.christen1@hes-so.ch"],
        "Es-tu daltonien ?",
        """
        <h1>Fait le test <a href="https://www.youtube.com/watch?v=ZzUsKizhb8o" target="_blank">ici</a></h1>
        """,
        is_html=True,
    )
