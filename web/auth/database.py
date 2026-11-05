import sqlite3
from pathlib import Path

# Project root:
# AI_VIRTUAL_MOUSE/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Database location:
# AI_VIRTUAL_MOUSE/web/auth/users.db
DATABASE_PATH = Path(__file__).resolve().parent / "users.db"


def get_connection():
    """Create and return a SQLite database connection."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection



def initialize_database():
    """Create the users and password-reset tables."""
    connection = get_connection()

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                expires_at INTEGER NOT NULL,
                used INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE CASCADE
            )
        """)

        connection.commit()

    finally:
        connection.close()



def create_user(username, email, password_hash):
    """Create a new user in the database."""
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
            """,
            (username, email, password_hash)
        )

        connection.commit()
        return cursor.lastrowid

    finally:
        connection.close()


def get_user_by_username(username):
    """Find a user by username."""
    connection = get_connection()

    try:
        return connection.execute(
            """
            SELECT id, username, email, password_hash, created_at
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

    finally:
        connection.close()


def get_user_by_email(email):
    """Find a user by email."""
    connection = get_connection()

    try:
        return connection.execute(
            """
            SELECT id, username, email, password_hash, created_at
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

    finally:
        connection.close()


def user_exists(username, email):
    """Check whether username or email is already registered."""
    connection = get_connection()

    try:
        result = connection.execute(
            """
            SELECT id
            FROM users
            WHERE username = ? OR email = ?
            LIMIT 1
            """,
            (username, email)
        ).fetchone()

        return result is not None

    finally:
        connection.close()

        
def get_user_by_id(user_id):
    """Find a user by their unique ID."""
    connection = get_connection()

    try:
        return connection.execute(
            """
            SELECT id, username, email, created_at
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        ).fetchone()

    finally:
        connection.close()
        
def update_user_profile(user_id, username, email):
    """Update a user's username and email address."""
    connection = get_connection()

    try:
        connection.execute(
            """
            UPDATE users
            SET username = ?, email = ?
            WHERE id = ?
            """,
            (username, email, user_id)
        )

        connection.commit()

    finally:
        connection.close()

        
def update_user_password(user_id, password_hash):
    """Update a user's password hash."""
    connection = get_connection()
    try:
        cursor = connection.execute(
            """
            UPDATE users
            SET password_hash = ?
            WHERE id = ?
            """,
            (password_hash, user_id)
        )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        connection.close()

        
def create_password_reset_token(user_id, token_hash, expires_at):
    """Store a hashed, expiring password-reset token."""
    connection = get_connection()
    try:
        connection.execute(
            "DELETE FROM password_reset_tokens WHERE user_id = ?",
            (user_id,)
        )
        connection.execute(
            """
            INSERT INTO password_reset_tokens
                (user_id, token_hash, expires_at, used)
            VALUES (?, ?, ?, 0)
            """,
            (user_id, token_hash, expires_at)
        )
        connection.commit()
    finally:
        connection.close()


def get_valid_password_reset_token(token_hash, now):
    """Return a valid, unused reset token, if one exists."""
    connection = get_connection()
    try:
        return connection.execute(
            """
            SELECT id, user_id
            FROM password_reset_tokens
            WHERE token_hash = ?
              AND used = 0
              AND expires_at > ?
            """,
            (token_hash, now)
        ).fetchone()
    finally:
        connection.close()


def reset_password_with_token(token_hash, now, password_hash):
    """Change a password and consume its token atomically."""
    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")

        token = connection.execute(
            """
            SELECT id, user_id
            FROM password_reset_tokens
            WHERE token_hash = ?
              AND used = 0
              AND expires_at > ?
            """,
            (token_hash, now)
        ).fetchone()

        if token is None:
            connection.rollback()
            return False

        cursor = connection.execute(
            """
            UPDATE users
            SET password_hash = ?
            WHERE id = ?
            """,
            (password_hash, token["user_id"])
        )

        if cursor.rowcount != 1:
            connection.rollback()
            return False

        # Consume this token and invalidate all other reset links
        # for this account.
        connection.execute(
            """
            UPDATE password_reset_tokens
            SET used = 1
            WHERE user_id = ?
            """,
            (token["user_id"],)
        )

        connection.commit()
        return True

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()



