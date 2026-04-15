import time
import signal
import sys
from src.config import load_config
from src.database import Database
from src.mail_client import MailClient
from src.email_classifier import EmailClassifier
from src.cv_extractor import CvExtractor
from src.k_drive_tools import KDriveTools


class Orchestrator:
    def __init__(self):
        self.config = load_config()
        self.db = Database(self.config)
        self.db.connect()
        self.db.drop_tables()
        self.db.ensure_tables()
        self.mail_client = MailClient(self.config)
        self.classifier = EmailClassifier(self.config)
        self.cv_extractor = CvExtractor(self.config)
        self.kdrive_tools = KDriveTools(self.config)
        self.running = False

    def start(self):
        self.running = True
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        try:
            print("Connecting to Infomaniak API...")
            self.mail_client.connect()
        except Exception as e:
            print(f"Failed to connect to API: {e}")
            return

        print(
            f"Email agent started. Polling every {self.config.poll_interval_seconds} seconds..."
        )

        while self.running:
            try:
                self.mail_client.disconnect()
                self.mail_client.connect()
                self._process_emails()
            except Exception as e:
                print(f"Error processing emails: {e}")

            for _ in range(self.config.poll_interval_seconds):
                if not self.running:
                    break
                time.sleep(1)

        self._cleanup()

    def _signal_handler(self, signum, frame):
        print("\nShutting down...")
        self.running = False

    def _process_emails(self):
        print("Fetching recent emails via REST API...")
        emails = self.mail_client.fetch_recent_emails(limit=50)
        print(f"Found {len(emails)} emails in inbox")

        new_job_applications = 0

        for email in emails:
            if self.db.email_exists(email.email_id):
                continue

            print(f"Checking email: {email.subject[:50]}...")

            is_job, attachment_index = self.classifier.is_job_application(email)

            if is_job:
                """
                self.kdrive_tools.upload_file(
                    email.attachments[attachment_index]['bytes'],
                    f"{email.email_id}.pdf",
                    self.config.kdrive_verified_directory_id
                )
                """
                extracted_cv = self.cv_extractor.extract_cv_to_json(
                    email.attachments[attachment_index]["bytes"]
                )

                self.db.save_job_application(
                    email_id=email.email_id,
                    sender_email=email.sender,
                    subject=email.subject,
                )
                new_job_applications += 1
                print(f"  -> Job application detected!")
            else:
                print(f"  -> Not a job application")

            self.db.create_email_entry(email.email_id, email.received_at)

        if len(emails) > 0:
            print(f"Batch processed: {new_job_applications} new job(s) found.")

    def _cleanup(self):
        self.mail_client.disconnect()
        self.db.close()
        print("Cleanup complete. Goodbye!")
