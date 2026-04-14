import imaplib
import email
from email.policy import default
from dataclasses import dataclass
from typing import List, Optional
import config


@dataclass
class Email:
    email_id: str
    subject: str
    sender: str
    body: str
    has_pdf_attachment: bool
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
        date = msg.get("Date", "")

        body = ""
        has_pdf = False

        # Parcours des parties MIME
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get_content_disposition())

            # Extraction du corps (priorité au texte brut)
            if content_type == "text/plain" and "attachment" not in disposition:
                if not body:  # On ne prend que la première partie texte
                    body = part.get_content()

            # Détection de pièce jointe PDF
            if "attachment" in disposition:
                filename = part.get_filename()
                if filename and filename.lower().endswith(".pdf"):
                    has_pdf = True

        return Email(
            email_id=email_id,
            subject=subject,
            sender=sender,
            body=body[:5000],  # Tronqué pour éviter de saturer le classifier
            has_pdf_attachment=has_pdf,
            received_at=date,
        )
