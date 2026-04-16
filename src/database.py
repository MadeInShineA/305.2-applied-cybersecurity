"""
Database module for the email agent application.

This module provides the Database class which manages all database connections
and operations for storing email processing data and job application records.
It uses PyMySQL to connect to a MySQL database and provides methods for
creating, reading, and updating data across multiple tables.
"""

from typing import Optional, List, Dict, Any

import pymysql
from pymysql.cursors import DictCursor

from src.config import Config


class Database:
    """
    Manages database connections and operations for email agent data storage.

    This class provides a centralized interface for all database operations
    in the email agent application. It handles connection management, table
    creation, and CRUD operations for emails, job applications, and job
    offer matches.

    The database schema includes three main tables:
        - emails: Tracks processed emails to avoid duplicate processing
        - job_applications: Stores information about detected job applications
        - job_offer_matches: Stores CV-to-job-offer matching results

    Attributes:
        config: Configuration object containing database credentials and settings.
        _connection: Internal PyMySQL connection object (None when disconnected).

    Example:
        >>> db = Database(config)
        >>> db.connect()
        >>> db.ensure_tables()
        >>> db.email_exists("msg-id-123")
        False
    """

    def __init__(self, config: Config) -> None:
        """
        Initialize the Database instance with configuration.

        Args:
            config: Config object containing database credentials and settings.
        """
        self.config = config
        self._connection: Optional[pymysql.Connection] = None

    def connect(self) -> None:
        """
        Establish connection to the MySQL database, creating it if it doesn't exist.

        This method connects to the MySQL server using credentials from the config,
        creates the database if it doesn't exist, and selects it for use. The
        database is created with utf8mb4 encoding to properly handle international
        characters in email content and CV data.

        Raises:
            pymysql.err.OperationalError: If unable to connect to MySQL server.
            pymysql.err.InternalError: If database creation fails.
        """
        self._connection = pymysql.connect(
            host=self.config.db_host,
            user=self.config.db_user,
            password=self.config.db_password,
            charset="utf8mb4",
            cursorclass=DictCursor,
        )

        with self._connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{self.config.db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )

        self._connection.select_db(self.config.db_name)

    def close(self) -> None:
        """
        Close the database connection.

        This method safely closes the database connection if one is active.
        It sets the internal connection reference to None after closing
        to ensure proper cleanup and prevent accidental reuse.
        """
        if self._connection:
            self._connection.close()
            self._connection = None

    def ensure_tables(self) -> None:
        """
        Create database tables if they don't exist.

        This method creates three tables necessary for the email agent:
        1. emails - stores processed email IDs to prevent duplicate processing
        2. job_applications - stores job application metadata
        3. job_offer_matches - stores CV-to-job-offer matching results

        Each table is created with appropriate constraints and indexes
        for efficient querying. Foreign key relationships maintain data
        integrity between tables.

        Note:
            This method automatically connects to the database if not already connected.
        """
        if not self._connection:
            self.connect()

        with self._connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS emails (
                    email_id VARCHAR(255) PRIMARY KEY,
                    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    received_at TIMESTAMP NULL

                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_applications (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email_id VARCHAR(255) UNIQUE NOT NULL,
                    sender_email VARCHAR(255),
                    subject VARCHAR(500),
                    classified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (email_id) REFERENCES emails(email_id)
                        ON DELETE CASCADE
                        ON UPDATE CASCADE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_offer_matches (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email_id VARCHAR(255) NOT NULL,
                    match_score INT,
                    offer_name VARCHAR(500),
                    offer_id VARCHAR(255),
                    strengths TEXT,
                    weaknesses TEXT,
                    recommendation TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (email_id) REFERENCES emails(email_id)
                        ON DELETE CASCADE
                        ON UPDATE CASCADE
                )
            """)

            self._connection.commit()

    def drop_tables(self) -> None:
        """
        Drop all database tables.

        WARNING: This method permanently deletes all data from the database.
        It drops tables in reverse order of dependencies (job_offer_matches,
        job_applications, emails) to respect foreign key constraints.

        This method is primarily used during development or testing to
        reset the database to a clean state.

        Note:
            This method automatically connects to the database if not already connected.
        """
        if not self._connection:
            self.connect()

        with self._connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS job_offer_matches")
            cursor.execute("DROP TABLE IF EXISTS job_applications")
            cursor.execute("DROP TABLE IF EXISTS emails")
            self._connection.commit()

    def email_exists(self, email_id: str) -> bool:
        """
        Check if an email has already been processed.

        This method queries the emails table to determine whether a given
        email (identified by its unique Message-ID) has already been processed
        by the email agent. This prevents duplicate processing of the same email.

        Args:
            email_id: The unique identifier of the email (Message-ID header).

        Returns:
            bool: True if the email exists in the database (already processed),
                  False otherwise.

        Note:
            This method automatically connects to the database if not already connected.
        """
        if not self._connection:
            self.connect()

        with self._connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM emails WHERE email_id = %s", (email_id,))
            return cursor.fetchone() is not None

    def create_email_entry(self, email_id: str, received_at: str) -> None:
        """
        Record a processed email in the database.

        This method inserts a new record into the emails table to track that
        an email has been processed. The record includes the email's unique
        identifier and the timestamp when it was received.

        Args:
            email_id: The unique identifier of the email (Message-ID header).
            received_at: The timestamp when the email was received (UTC format).

        Note:
            This method automatically connects to the database if not already connected.
            Uses INSERT IGNORE to avoid errors if the email was already inserted.
        """
        if not self._connection:
            self.connect()

        with self._connection.cursor() as cursor:
            cursor.execute(
                "INSERT IGNORE INTO emails (email_id, received_at) VALUES (%s, %s)",
                (email_id, received_at),
            )
            self._connection.commit()

    def save_job_application(
        self,
        email_id: str,
        sender_email: str,
        subject: str,
    ) -> bool:
        """
        Save a job application entry to the database.

        This method stores information about a detected job application in the
        job_applications table. It records the email ID, sender's email address,
        and email subject for future reference and analysis.

        Args:
            email_id: The unique identifier of the original email.
            sender_email: The email address of the job applicant.
            subject: The subject line of the job application email.

        Returns:
            bool: True if the job application was saved successfully, False if
                  it already exists (duplicate entry).

        Raises:
            Exception: If a database error occurs other than duplicate entry.

        Note:
            This method automatically connects to the database if not already connected.
        """
        if not self._connection:
            self.connect()

        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO job_applications
                    (email_id, sender_email, subject)
                    VALUES (%s, %s, %s)
                    """,
                    (email_id, sender_email, subject),
                )
                self._connection.commit()
            return True
        except pymysql.err.IntegrityError:
            return False
        except Exception:
            raise

    def save_job_offer_comparison(
        self,
        email_id: str,
        match_score: int,
        offer_name: str,
        offer_id: str,
        strengths: str,
        weaknesses: str,
        recommendation: str,
    ) -> bool:
        """
        Save a job offer comparison summary to the database.

        This method stores the results of matching a candidate's CV against
        available job offers. It records the match score, best matching offer
        details, strengths and weaknesses of the candidate, and a recommendation.

        Args:
            email_id: The unique identifier of the original application email.
            match_score: The numerical score (0-100) indicating how well the
                         candidate matches the job offer.
            offer_name: The name/title of the best matching job offer.
            offer_id: The unique identifier of the best matching job offer.
            strengths: Comma-separated list of candidate's strengths relative
                       to the job requirements.
            weaknesses: Comma-separated list of candidate's weaknesses or
                        gaps relative to the job requirements.
            recommendation: Text recommendation based on the match analysis.

        Returns:
            bool: True if the comparison was saved successfully.

        Raises:
            Exception: If a database error occurs during insertion.

        Note:
            This method automatically connects to the database if not already connected.
        """
        if not self._connection:
            self.connect()

        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO job_offer_matches
                    (email_id, match_score, offer_name, offer_id, strengths, weaknesses, recommendation)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        email_id,
                        match_score,
                        offer_name,
                        offer_id,
                        strengths,
                        weaknesses,
                        recommendation,
                    ),
                )
                self._connection.commit()
            return True
        except Exception:
            raise
