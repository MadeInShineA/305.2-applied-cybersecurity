import pymysql
from typing import Optional, Set
from config import Config, load_config


class Database:
    def __init__(self, config: Config):
        self.config = config
        self._connection: Optional[pymysql.Connection] = None

    def connect(self) -> None:
        self._connection = pymysql.connect(
            host=self.config.db_host,
            user=self.config.db_user,
            password=self.config.db_password,
            database=self.config.db_name,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
        )

    def close(self) -> None:
        if self._connection:
            self._connection.close()
            self._connection = None

    def ensure_tables(self) -> None:
        if not self._connection:
            self.connect()

        with self._connection.cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS checked_emails (
                    email_id VARCHAR(255) PRIMARY KEY,
                    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS job_applications (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email_id VARCHAR(255) UNIQUE NOT NULL,
                    sender_email VARCHAR(255),
                    subject VARCHAR(500),
                    received_at TIMESTAMP NULL,
                    classified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            self._connection.commit()

    def drop_tables(self) -> None:
        if not self._connection:
            self.connect()

        with self._connection.cursor() as cursor:
            cursor.execute('DROP TABLE IF EXISTS checked_emails')
            cursor.execute('DROP TABLE IF EXISTS job_applications')
            self._connection.commit()

    def is_email_checked(self, email_id: str) -> bool:
        if not self._connection:
            self.connect()

        with self._connection.cursor() as cursor:
            cursor.execute(
                'SELECT 1 FROM checked_emails WHERE email_id = %s',
                (email_id,)
            )
            return cursor.fetchone() is not None

    def mark_email_checked(self, email_id: str) -> None:
        if not self._connection:
            self.connect()

        with self._connection.cursor() as cursor:
            cursor.execute(
                'INSERT IGNORE INTO checked_emails (email_id) VALUES (%s)',
                (email_id,)
            )
            self._connection.commit()

    def save_job_application(
        self,
        email_id: str,
        sender_email: str,
        subject: str,
        received_at: Optional[str] = None
    ) -> bool:
        if not self._connection:
            self.connect()

        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    '''
                    INSERT INTO job_applications 
                    (email_id, sender_email, subject, received_at) 
                    VALUES (%s, %s, %s, %s)
                    ''',
                    (email_id, sender_email, subject, received_at)
                )
                self._connection.commit()
            return True
        except pymysql.err.IntegrityError:
            return False


def get_database() -> Database:
    config = load_config()
    db = Database(config)
    db.connect()
    db.ensure_tables()
    return db