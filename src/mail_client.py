import imaplib
import email
import datetime
from email.policy import default
from email.utils import parsedate_to_datetime
from dataclasses import dataclass
from typing import List, Optional
import config
import pdfplumber
from io import BytesIO


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
    def __init__(self, config: config.Config):
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
        Closes the connection safely.
        """
        if self._connection:
            try:
                self._connection.close()
                self._connection.logout()
            except Exception:
                pass
            self._connection = None

    def fetch_recent_emails(self, limit: int = 50) -> List[Email]:
        """
        Fetches the most recent emails using IMAP commands.
        """
        if not self._connection:
            self.connect()

        # Recherche des IDs de tous les messages
        status, messages = self._connection.search(None, "ALL")
        if status != "OK":
            return []

        # Récupération des derniers IDs (triés par limit)
        msg_ids = messages[0].split()
        latest_ids = msg_ids[-limit:]
        latest_ids.reverse()  # Du plus récent au plus ancien

        emails = []
        for msg_id in latest_ids:
            # Fetch du contenu brut (RFC822)
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
            if "attachment" in disposition.lower() or content_type.startswith("application/pdf"):
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
                                
                                attachments.append({
                                    "filename": filename,
                                    "bytes": pdf_bytes,
                                    "data": full_text,
                                    "metadata": pdf.metadata
                                })
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
