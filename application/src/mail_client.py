"""
Mail client module for the email agent application.

This module provides the MailClient class which handles all email operations
including IMAP for receiving emails and SMTP for sending emails. It also
includes utilities for parsing email content and extracting PDF attachments.

The module supports:
- IMAP email retrieval with PDF attachment extraction
- SMTP email sending with HTML support
- Email date parsing for database storage
- PDF text extraction using pdfplumber
"""

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
    """
    Parse email date string to UTC datetime for MySQL storage.

    This utility function converts the date string from email headers
    (in RFC 2822 format) to a standardized string format suitable
    for MySQL TIMESTAMP storage.

    Args:
        date_str: The date string from email headers (e.g., "Wed, 15 Apr 2026 10:30:00 +0200").

    Returns:
        Optional[str]: A formatted datetime string in "%Y-%m-%d %H:%M:%S" format,
                      or None if parsing fails.

    Example:
        >>> parse_email_date("Wed, 15 Apr 2026 10:30:00 +0200")
        '2026-04-15 08:30:00'
    """
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
    """
    Data class representing a parsed email message.

    This class encapsulates all relevant information extracted from an email,
    including metadata (ID, subject, sender), content (body), and attachments.
    It is used throughout the application to pass email data between components.

    Attributes:
        email_id: Unique identifier (Message-ID header) for the email.
        subject: The email subject line.
        sender: The sender's email address (From header).
        body: The email body content (plain text, truncated to 5000 chars).
        has_pdf_attachment: Boolean indicating if the email contains PDF attachments.
        attachments: List of attachment dictionaries with 'filename', 'bytes', 'data', and 'metadata'.
        received_at: Optional timestamp of when the email was received.
    """

    email_id: str
    subject: str
    sender: str
    body: str
    has_pdf_attachment: bool
    attachments: dict
    received_at: Optional[str] = None


class MailClient:
    """
    Client for IMAP email operations with PDF attachment extraction.

    This class provides a unified interface for receiving emails via IMAP
    and sending emails via SMTP. It handles connection management, email
    parsing, and PDF attachment text extraction.

    The class supports:
    - Connecting to IMAP servers to fetch recent emails
    - Parsing raw email content including MIME multipart messages
    - Extracting text from PDF attachments
    - Sending emails via SMTP with HTML support

    Attributes:
        config: Configuration object containing email server credentials.
        _connection: Internal IMAP4_SSL connection object (None when disconnected).

    Example:
        >>> client = MailClient(config)
        >>> client.connect()
        >>> emails = client.fetch_recent_emails(limit=10)
        >>> client.send_email(["recipient@example.com"], "Subject", "Body")
        >>> client.disconnect()
    """

    def __init__(self, config: Config) -> None:
        """
        Initialize the MailClient with configuration.

        Args:
            config: Config object containing email server credentials and settings.
        """
        self.config = config
        self._connection: Optional[imaplib.IMAP4_SSL] = None

    def connect(self) -> None:
        """
        Connect to the IMAP server using mail_imap_host and mail_password.

        This method establishes an SSL connection to the IMAP server,
        authenticates using the configured credentials, and selects
        the INBOX folder for subsequent operations.

        Raises:
            Exception: If connection or authentication fails.
            imaplib.IMAP4.error: If the IMAP server returns an error.
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
        Close the IMAP connection safely.

        This method gracefully closes the IMAP connection by first
        closing the selected mailbox and then logging out. Any exceptions
        during cleanup are silently caught to prevent disruption.

        Note:
            The internal connection reference is set to None after
            disconnection to prevent accidental reuse.
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
        Send an email via SMTP using mail_smtp_host and mail_smtp_port.

        This method constructs a MIME multipart message and sends it via
        the configured SMTP server. It supports both plain text and HTML
        email formats. The method handles both explicit TLS (port 587)
        and implicit SSL (port 465) connections.

        Args:
            to_addresses: List of recipient email addresses.
            subject: The email subject line.
            body: The email body content (plain text or HTML).
            is_html: If True, the body is treated as HTML; otherwise as plain text.

        Raises:
            Exception: If SMTP connection or sending fails.
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

    def answer_email(
        self,
        original_email: Email,
        body: str,
        subject: Optional[str] = None,
        is_html: bool = False,
        cc_addresses: Optional[List[str]] = None,
    ) -> None:
        """
        Send a reply email via SMTP, properly threaded to the original email.

        This method constructs a MIME multipart message that replies to a
        specific email by setting appropriate headers (In-Reply-To, References)
        for proper email threading in mail clients.

        Args:
            original_email: The Email object being replied to (contains email_id).
            body: The reply body content (plain text or HTML).
            subject: Optional custom subject. If None, uses "Re: {original_subject}".
            is_html: If True, the body is treated as HTML; otherwise as plain text.
            cc_addresses: Optional list of CC recipient email addresses.

        Raises:
            Exception: If SMTP connection or sending fails.

        Note:
            - Automatically extracts the original sender from original_email.sender
            - Adds "Re: " prefix to subject if not already present
            - Sets In-Reply-To and References headers for email threading
            - Reply-To is set to the original sender by default
        """
        msg = MIMEMultipart()
        msg["From"] = self.config.mail_email

        # Extract recipient from original email's sender
        # Handle cases where sender might be "Name <email>" format
        original_sender = original_email.sender
        if "<" in original_sender and ">" in original_sender:
            # Extract email address from "Name <email@domain.com>" format
            original_sender = original_sender.split("<")[1].split(">")[0].strip()

        msg["To"] = original_sender
        msg["In-Reply-To"] = original_email.email_id
        msg["References"] = original_email.email_id

        # Handle subject with Re: prefix
        if subject is None:
            original_subject = original_email.subject
            if not original_subject.lower().startswith("re:"):
                subject = f"Re: {original_subject}"
            else:
                subject = original_subject
        msg["Subject"] = subject

        # Add CC recipients if provided
        if cc_addresses:
            msg["Cc"] = ", ".join(cc_addresses)

        mime_type = "html" if is_html else "plain"
        msg.attach(MIMEText(body, mime_type))

        # Build recipient list (To + CC)
        to_addresses = [original_sender]
        if cc_addresses:
            to_addresses.extend(cc_addresses)

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
            raise Exception(f"Failed to send reply email: {e}")

    def fetch_recent_emails(self, limit: int = 50) -> List[Email]:
        """
        Fetch the most recent emails using IMAP commands.

        This method retrieves the most recent emails from the INBOX folder.
        It fetches the email IDs in reverse chronological order and parses
        each raw email into an Email object with extracted content and
        PDF attachments.

        The method automatically connects to the IMAP server if not already
        connected. It fetches emails in batches to improve performance.

        Args:
            limit: Maximum number of recent emails to fetch (default: 50).

        Returns:
            List[Email]: A list of Email objects parsed from the raw email data.
                         Returns an empty list if no emails are found or on error.

        Note:
            The method sorts emails by chronological order (oldest to newest)
            but fetches the most recent ones first from the IMAP server.
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
        Parse raw bytes into a structured Email object.

        This internal method handles the complex task of parsing raw email
        bytes according to RFC 822/2822 standards. It extracts the email
        metadata (ID, subject, sender, date) and processes MIME multipart
        messages to extract the body and PDF attachments.

        The method walks through all MIME parts of the email message:
        - text/plain parts are extracted as the email body (first occurrence only)
        - text/html parts are ignored (plain text is preferred)
        - application/pdf parts with attachment disposition are extracted as files

        For PDF attachments, the method uses pdfplumber to extract text content
        from each page, preserving the reading order and column layout.

        Args:
            raw_email: Raw bytes representing the complete email message.

        Returns:
            Email: A structured Email object with extracted content and attachments.

        Note:
            - Email body is truncated to 5000 characters to prevent memory issues.
            - PDF extraction failures silently set has_pdf to False.
            - The method uses email.policy.default for modern parsing behavior.
        """
        msg = email.message_from_bytes(raw_email, policy=default)

        # Extract email headers (Message-ID, Subject, From, Date)
        email_id = msg.get("Message-ID", "unknown")
        subject = msg.get("Subject", "No Subject")
        sender = msg.get("From", "Unknown Sender")
        date_str = msg.get("Date", "")
        received_at = parse_email_date(date_str)

        # Initialize variables for body and attachments
        body = ""
        has_pdf = False
        attachments = []

        # Iterate through MIME parts to extract content and attachments
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = part.get_content_disposition() or ""

            # Extract body (prefer plain text, skip attachments)
            if content_type == "text/plain" and "attachment" not in disposition:
                if not body:  # Only take the first text part
                    body = part.get_content()

            # Detect and extract PDF attachments
            if "attachment" in disposition.lower() or content_type.startswith(
                "application/pdf"
            ):
                filename = part.get_filename()
                if filename and filename.lower().endswith(".pdf"):
                    has_pdf = True
                    # Get raw PDF bytes from the attachment
                    pdf_bytes = part.get_payload(decode=True)

                    if pdf_bytes:
                        try:
                            # Extract text from PDF using pdfplumber
                            with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
                                # Extract text from each page, respecting columns and reading order
                                pages_text = []
                                for page in pdf.pages:
                                    page_text = page.extract_text() or ""
                                    pages_text.append(page_text)

                                # Join pages with double newlines for separation
                                full_text = "\n\n".join(pages_text)

                                # Store attachment metadata and extracted content
                                attachments.append(
                                    {
                                        "filename": filename,
                                        "bytes": pdf_bytes,
                                        "data": full_text,
                                        "metadata": pdf.metadata,
                                    }
                                )
                        except Exception as _:
                            # Silently handle PDF extraction failures
                            has_pdf = False

        # Construct and return the Email object
        return Email(
            email_id=email_id,
            subject=subject,
            sender=sender,
            body=body[:5000],  # Truncate body to prevent memory issues
            has_pdf_attachment=has_pdf,
            attachments=attachments,
            received_at=received_at,
        )


if __name__ == "__main__":
    # Main block for testing the MailClient functionality
    # This allows testing email sending without running the full application

    from src.config import load_config

    config = load_config()

    mail_client = MailClient(config)

    # Send a test email with HTML content
    mail_client.send_email(
        ["loic.christen1@hes-so.ch"],
        "Es-tu daltonien ?",
        """
        <h1>Fait le test <a href="https://www.youtube.com/watch?v=ZzUsKizhb8o" target="_blank">ici</a></h1>
        """,
        is_html=True,
    )
