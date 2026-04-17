"""
Orchestrator module for the email agent application.

This module provides the Orchestrator class which coordinates all components
of the email agent system. It manages the main processing loop, handling
email polling, classification, CV extraction, verification, matching,
and response generation.

The orchestrator follows this workflow for each email:
1. Poll email inbox for new messages
2. Check if email is a job application with a CV attachment
3. Extract CV data from PDF using Docling and LLM
4. Verify CV authenticity using web search
5. Match CV against available job offers
6. Generate and send a professional response
7. Store results in the database

The class handles graceful shutdown via signal handlers (SIGINT, SIGTERM)
and ensures proper cleanup of resources on exit.
"""

import signal
import time
from typing import List

from docling.document_converter import DocumentConverter

from src.application_matcher import ApplicationMatcher
from src.config import load_config, Config
from src.cv_extractor import CvExtractor
from src.cv_veracity_checker import CvVeracityChecker
from src.database import Database
from src.email_classifier import EmailClassifier
from src.k_drive_tools import KDriveTools
from src.mail_client import MailClient, Email
from src.email_answer_generator import EmailAnswerGenerator, EmailAnswer


class Orchestrator:
    """
    Central coordinator for the email agent application.

    This class orchestrates the entire email processing pipeline, managing
    all components and their interactions. It handles the main event loop
    that polls for new emails and processes each one through the complete
    workflow from detection to response.

    The orchestrator initializes and manages:
    - Database connection and schema management
    - Mail client for IMAP/SMTP operations
    - Email classifier for job application detection
    - CV extractor for PDF to JSON conversion
    - CV verifier for authenticity checking
    - Application matcher for job offer comparison
    - Email answer generator for response creation

    Attributes:
        config: Configuration object with all settings.
        converter: Docling DocumentConverter for PDF processing.
        db: Database instance for data storage.
        mail_client: MailClient for email operations.
        classifier: EmailClassifier for job application detection.
        cv_extractor: CvExtractor for PDF text extraction.
        kdrive_tools: KDriveTools for file storage operations.
        cv_veracity_checker: CvVeracityChecker for CV verification.
        matcher: ApplicationMatcher for job offer matching.
        email_answer_generator: EmailAnswerGenerator for response generation.
        running: Boolean flag indicating if the main loop is active.

    Example:
        >>> orchestrator = Orchestrator()
        >>> orchestrator.start()
        # Application runs indefinitely until interrupted
    """

    def __init__(self) -> None:
        """
        Initialize the Orchestrator and all its components.

        This constructor sets up all necessary components for the email agent:
        - Loads configuration from environment variables
        - Initializes the database (drops and recreates tables)
        - Creates instances of all processing components

        Note:
            - Database tables are dropped and recreated on initialization
              to ensure a clean state.
            - The running flag is initialized to False and set to True
              when start() is called.
        """
        # Load configuration from environment variables
        self.config: Config = load_config()

        # Initialize Docling converter for PDF processing
        self.converter = DocumentConverter()

        # Initialize database and set up schema
        self.db = Database(self.config)
        self.db.connect()
        # Drop existing tables and create fresh schema
        self.db.drop_tables()
        self.db.ensure_tables()

        # Initialize email client
        self.mail_client = MailClient(self.config)

        # Initialize email classifier for job application detection
        self.classifier = EmailClassifier(self.config)

        # Initialize CV extractor with converter
        self.cv_extractor = CvExtractor(self.config, self.converter)

        # Initialize kDrive tools for file storage
        self.kdrive_tools = KDriveTools(self.config)

        # Initialize CV veracity checker for authenticity verification
        self.cv_veracity_checker = CvVeracityChecker(self.config)

        # Initialize application matcher for job offer comparison
        self.matcher = ApplicationMatcher(self.config, self.kdrive_tools)

        # Initialize email answer generator for response creation
        self.email_answer_generator = EmailAnswerGenerator(self.config)

        # Initialize running state flag
        self.running = False

    def start(self) -> None:
        """
        Start the email agent processing loop.

        This method initiates the main event loop that continuously polls
        for new emails and processes them. It sets up signal handlers for
        graceful shutdown and enters the polling cycle.

        The loop runs until:
        - A SIGINT or SIGTERM signal is received (Ctrl+C or termination)
        - An unrecoverable exception occurs

        Processing steps per iteration:
        1. Disconnect and reconnect to ensure fresh connection
        2. Fetch recent emails from inbox
        3. Process each email through the complete workflow
        4. Wait for the configured poll interval

        Note:
            - The method blocks indefinitely and should be run in the main thread.
            - On shutdown, _cleanup() is called to close connections properly.
        """
        # Set running flag to True
        self.running = True

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Initial connection to mail server
        try:
            print("Connecting to Infomaniak API...")
            self.mail_client.connect()
        except Exception as e:
            print(f"Failed to connect to API: {e}")
            return

        # Print startup message with poll interval
        print(
            f"Email agent started. Polling every {self.config.poll_interval_seconds} seconds..."
        )

        # Main processing loop
        while self.running:
            try:
                # Reconnect to ensure fresh connection for each batch
                self.mail_client.disconnect()
                self.mail_client.connect()
                # Process all new emails
                self._process_emails()
            except Exception as e:
                print(f"Error processing emails: {e}")

            # Wait for the configured poll interval (countdown in seconds)
            for _ in range(self.config.poll_interval_seconds):
                if not self.running:
                    break
                time.sleep(1)

        # Perform cleanup when loop exits
        self._cleanup()

    def _signal_handler(self, signum: int, frame) -> None:
        """
        Handle shutdown signals (SIGINT, SIGTERM).

        This internal method is called when the process receives an
        interrupt signal (Ctrl+C) or termination signal. It sets the
        running flag to False to gracefully exit the main loop.

        Args:
            signum: The signal number (SIGINT or SIGTERM).
            frame: The current stack frame (unused, required by signal handler).

        Note:
            - This method is registered as a signal handler in start().
            - The print statement adds a newline before the message for clean output.
        """
        print("\nShutting down...")
        self.running = False

    def _process_emails(self) -> None:
        """
        Process a batch of recent emails through the complete workflow.

        This method handles the core processing logic for each email:
        1. Fetch recent emails from the inbox
        2. Check if already processed (via database)
        3. Classify as job application or skip
        4. For job applications:
           a. Extract CV data from PDF
           b. Verify CV authenticity
           c. If verified: match against jobs, generate and send response
           d. If not verified: store in separate directory
        5. Store results in database
        6. Upload CV files to appropriate kDrive directories

        The method logs progress throughout the process for monitoring.

        Note:
            - Only processes emails not already in the database.
            - Verified CVs go to the verified directory; unverified to the other.
            - Match results and email responses are logged and stored.
        """
        # Fetch recent emails using the mail client
        print("Fetching recent emails via IMAP...")
        emails: List[Email] = self.mail_client.fetch_recent_emails(limit=50)
        print(f"Found {len(emails)} emails in inbox")

        # Initialize counter for new job applications found
        new_job_applications = 0

        # Display separator for batch processing
        print("=" * 50)
        print(f"Processing batch of {len(emails)} emails...")
        print("=" * 50)

        # Process each email in the batch
        for email in emails:
            try:
                # Check if this email has already been processed
                if self.db.email_exists(email.email_id):
                    continue

                # Record the email in the database as processed
                self.db.create_email_entry(email.email_id, email.received_at)

                # Log which email we're checking
                print(
                    f"Checking email:\n\tsender:{email.sender}\n\tsubject:{email.subject[:50]}..."
                )

                # Check if this is a job application with CV
                is_job, attachment_index = self.classifier.is_job_application(email)

                # Handle job applications
                if is_job:
                    print("Job application detected!")

                    # Extract CV data from the PDF attachment
                    extracted_cv = self.cv_extractor.extract_cv_to_json(
                        email.attachments[attachment_index]["bytes"]
                    )

                    # Extract candidate name from the CV data
                    person_data = extracted_cv.get("person", {})
                    candidate_name = person_data.get("name", "unknown")

                    # Generate a filename based on candidate name or sender
                    file_name = (
                        candidate_name.lower().replace(" ", "-")
                        if candidate_name
                        else f"cv-{email.sender}"
                    )

                    # Ensure we have a valid filename
                    if not file_name:
                        file_name = f"cv-{email.sender}"

                    print(f"Extracted cv for: {file_name if file_name else 'unknown'}")

                    # Verify the CV authenticity using web search
                    cv_verification_score = self.cv_veracity_checker.verify_cv(
                        extracted_cv
                    )

                    print(
                        f"The cv got a verification score of: {cv_verification_score}"
                    )

                    # Determine if CV is verified based on score threshold
                    is_cv_verified = cv_verification_score >= 50

                    # Handle verified CVs
                    if is_cv_verified:
                        print("Cv classified as verified")

                        # Upload CV to verified directory on kDrive
                        self.kdrive_tools.upload_file(
                            email.attachments[attachment_index]["bytes"],
                            file_name,
                            self.config.kdrive_verified_directory_id,
                        )

                        print("Cv file saved on Kdrive")

                        # Compare CV against available job offers
                        match_score, best_match_offer, best_report = (
                            self.matcher.compare_with_offers(extracted_cv)
                        )

                        # Log the match score
                        print(f"Best match score: {match_score}")

                        # Store the job offer comparison in the database
                        self.db.save_job_offer_comparison(
                            email_id=email.email_id,
                            match_score=match_score,
                            offer_name=best_match_offer.get("name", ""),
                            offer_id=best_match_offer.get("id", ""),
                            strengths=str(best_report.get("strengths", [])),
                            weaknesses=str(best_report.get("weaknesses", [])),
                            recommendation=best_report.get("recommendation", ""),
                        )

                        # Generate a professional email response
                        email_answer: EmailAnswer = (
                            self.email_answer_generator.generate_email_answer(
                                email, candidate_name, best_match_offer
                            )
                        )

                        print("Email answer generated")

                        # Send the response email to the applicant
                        self.mail_client.answer_email(
                            original_email=email,
                            body=email_answer.body,
                            subject=email.subject,
                        )

                        print("Email answer sent")

                        # Increment counter for new job applications
                        new_job_applications += 1

                    # Handle non-verified CVs
                    else:
                        print("Cv classified as not verified")

                        # Upload CV to the not-verified directory on kDrive
                        self.kdrive_tools.upload_file(
                            email.attachments[attachment_index]["bytes"],
                            file_name,
                            self.config.kdrive_not_verified_directory_id,
                        )

                        print("Cv file saved on Kdrive")

                # Handle non-job-application emails
                else:
                    print("Not a job application")

                # Display separator after processing each email
                print("-" * 50)
            except Exception as e:
                print(f"Error processing email {email.email_id}: {e}")
                print("-" * 50)

        # Print summary if we processed any emails
        if len(emails) > 0:
            print(f"Batch processed: {new_job_applications} new job(s) found.")

    def _cleanup(self) -> None:
        """
        Clean up resources on shutdown.

        This method is called when the orchestrator stops running.
        It ensures all connections are properly closed:
        - Disconnects from the mail server
        - Closes the database connection

        Note:
            - This method is called automatically by start() when exiting.
            - Resources are cleaned up in reverse order of initialization.
        """
        # Disconnect from mail server
        self.mail_client.disconnect()

        # Close database connection
        self.db.close()

        print("Cleanup complete. Goodbye!")
