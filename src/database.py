from typing import Optional

import pymysql

from src.config import Config


class Database:
    """Manages database connections and operations for email agent data storage."""

    def __init__(self, config: Config):
        self.config = config
        self._connection: Optional[pymysql.Connection] = None

    def connect(self) -> None:
        """Establish connection to the MySQL database, creating it if it doesn't exist."""
        self._connection = pymysql.connect(
            host=self.config.db_host,
            user=self.config.db_user,
            password=self.config.db_password,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )

        with self._connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{self.config.db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )

        self._connection.select_db(self.config.db_name)

    def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    def ensure_tables(self) -> None:
        """Create database tables if they don't exist."""
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
        """Drop all database tables."""
        if not self._connection:
            self.connect()

        with self._connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS job_offer_matches")
            cursor.execute("DROP TABLE IF EXISTS job_applications")
            cursor.execute("DROP TABLE IF EXISTS emails")
            self._connection.commit()

    def email_exists(self, email_id: str) -> bool:
        """Check if an email has already been processed."""
        if not self._connection:
            self.connect()

        with self._connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM emails WHERE email_id = %s", (email_id,))
            return cursor.fetchone() is not None

    def create_email_entry(self, email_id: str, received_at: str) -> None:
        """Record a processed email in the database."""
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
        """Save a job application entry to the database."""
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
        """Save a job offer comparison summary to the database."""
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
