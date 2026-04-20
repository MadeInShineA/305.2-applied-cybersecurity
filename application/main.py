"""
Main entry point for the email agent application.

This module provides the entry point for running the email agent.
The email agent is an automated system that:
- Polls an email inbox for new messages
- Detects job applications with CV attachments
- Extracts structured data from CV PDFs
- Verifies CV authenticity via web search
- Matches candidates against available job offers
- Generates and sends professional response emails
- Stores all processing results in a database

The application runs indefinitely until interrupted (Ctrl+C or SIGTERM).

Usage:
    python main.py

The application requires:
- A .env file with all required API keys and credentials
- A MySQL database accessible with the configured credentials
- Access to Infomaniak kDrive for job offers and CV storage
- Access to an IMAP email account for receiving applications
- Access to an SMTP server for sending response emails

See README.md for detailed setup instructions.
"""

from src.orchestrator import Orchestrator


def main() -> None:
    """
    Initialize and start the email agent orchestrator.

    This function creates an instance of the Orchestrator class
    and calls its start() method to begin the email processing loop.

    The orchestrator manages all components of the system and
    handles the main event loop that polls for new emails.

    Note:
        - This function blocks indefinitely until interrupted
        - On interruption, the orchestrator performs cleanup automatically
    """
    # Create a new orchestrator instance
    orchestrator = Orchestrator()

    # Start the email processing loop
    orchestrator.start()


if __name__ == "__main__":
    # Run the main function when the script is executed directly
    main()
