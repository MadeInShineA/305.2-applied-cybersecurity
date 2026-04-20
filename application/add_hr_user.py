"""
CLI script to add a new HR user to the database.
Run this from the project root.
"""

import getpass
import bcrypt
import pymysql

from src.config import load_config
from src.database import Database


def main():
    print("--- Create New HR User ---")

    # 1. Collect user inputs
    username = input("Username: ").strip()
    if not username:
        print("Error: Username cannot be empty.")
        return

    password = getpass.getpass("Password (hidden): ")
    if not password:
        print("Error: Password cannot be empty.")
        return

    full_name = input("Full Name (e.g., Lara Clète): ").strip()
    job_title = input("Job Title (e.g., Cheffe RH): ").strip()
    phone = input("Phone Number (e.g., +41 79 123 45 67): ").strip()

    # 2. Hash the password securely
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    # 3. Connect to the database and insert
    config = load_config()
    db = Database(config)

    try:
        db.connect()
        # Ensure the hr_users table exists before trying to insert
        db.ensure_tables()

        with db._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO hr_users (username, password_hash, full_name, job_title, phone)
                VALUES (%s, %s, %s, %s, %s)
            """,
                (username, password_hash, full_name, job_title, phone),
            )

        db._connection.commit()
        print(
            f"\n[SUCCESS] HR user '{username}' has been successfully added to the database."
        )

    except pymysql.err.IntegrityError:
        print(f"\n[ERROR] The username '{username}' already exists in the database.")
    except Exception as e:
        print(f"\n[ERROR] A database error occurred: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
