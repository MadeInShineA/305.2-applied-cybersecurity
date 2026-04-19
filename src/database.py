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
                    received_at TIMESTAMP NULL,
                    subject VARCHAR(255),
                    body VARCHAR(255)

                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_applications (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email_id VARCHAR(255) UNIQUE NOT NULL,
                    candidate_email VARCHAR(255),
                    candidate_name VARCHAR(255),
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

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hr_responses (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    match_id INT NOT NULL,
                    hr_email_sent BOOLEAN DEFAULT FALSE,
                    sent_at TIMESTAMP NULL,
                    candidate_email VARCHAR(255),
                    offer_name VARCHAR(500),
                    email_subject VARCHAR(500),
                    email_body VARCHAR(5000),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (match_id) REFERENCES job_offer_matches(id)
                        ON DELETE CASCADE
                        ON UPDATE CASCADE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hr_users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    full_name VARCHAR(255) NOT NULL,
                    job_title VARCHAR(255) NOT NULL,
                    phone VARCHAR(50) NOT NULL
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
            cursor.execute("DROP TABLE IF EXISTS hr_responses")
            cursor.execute("DROP TABLE IF EXISTS job_offer_matches")
            cursor.execute("DROP TABLE IF EXISTS job_applications")
            cursor.execute("DROP TABLE IF EXISTS emails")
            cursor.execute("DROP TABLE IF EXISTS hr_users")
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

    def create_email_entry(
        self, email_id: str, received_at: str, email_subject: str, email_body: str
    ) -> None:
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
                "INSERT IGNORE INTO emails (email_id, received_at, subject, body) VALUES (%s, %s, %s, %s)",
                (email_id, received_at, email_subject, email_body),
            )
            self._connection.commit()

    def save_job_application(
        self,
        email_id: str,
        candidate_email: str,
        candidate_name: str,
    ) -> bool:
        """
        Save a job application entry to the database.

        This method stores information about a detected job application in the
        job_applications table. It records the email ID, sender's email address,
        and email subject for future reference and analysis.

        Args:
            email_id: The unique identifier of the original email.
            candidate_email: The email address of the job applicant.

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
                    (email_id, candidate_email, candidate_name)
                    VALUES (%s, %s, %s)
                    """,
                    (email_id, candidate_email, candidate_name),
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

    def get_candidate_job_matches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve candidate/job offer matches from the database.

        Args:
            limit: Maximum number of records to return (default 10).

        Returns:
            List of dictionaries containing match information.
        """
        if not self._connection:
            self.connect()

        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    e.subject,
                    e.received_at,
                    e.body,
                    m.id,
                    m.email_id,
                    m.match_score,
                    m.offer_name,
                    m.offer_id,
                    m.strengths,
                    m.weaknesses,
                    m.recommendation,
                    a.candidate_email,
                    a.candidate_name,
                    r.hr_email_sent
                FROM job_offer_matches m
                JOIN job_applications a ON m.email_id = a.email_id
                JOIN emails e ON m.email_id = e.email_id
                LEFT JOIN hr_responses r ON m.id = r.match_id
                ORDER BY m.match_score DESC
                LIMIT %s
            """,
                (limit,),
            )
            return cursor.fetchall()

    def is_match_processed_by_hr(self, match_id: int) -> bool:
        """
        Check if a candidate/job match has already been processed by HR.

        Args:
            match_id: The ID of the job_offer_matches record.

        Returns:
            bool: True if HR has already sent a response, False otherwise.
        """
        if not self._connection:
            self.connect()

        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT hr_email_sent 
                FROM hr_responses 
                WHERE match_id = %s AND hr_email_sent = TRUE
            """,
                (match_id,),
            )
            return cursor.fetchone() is not None

    def save_hr_response(
        self,
        match_id: int,
        candidate_email: str,
        offer_name: str,
        email_subject: str,
        email_body: str,
    ) -> bool:
        """
        Record an HR response to a candidate/job match.

        Args:
            match_id: The ID of the job_offer_matches record.
            candidate_email: The email address of the candidate.
            offer_name: The name of the job offer.

        Returns:
            bool: True if the response was saved successfully.
        """
        if not self._connection:
            self.connect()

        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO hr_responses
                    (match_id, candidate_email, offer_name, email_subject, email_body)
                    VALUES (%s, %s, %s, %s, %s)
                """,
                    (match_id, candidate_email, offer_name, email_subject, email_body),
                )
                self._connection.commit()
            return True
        except Exception:
            raise
