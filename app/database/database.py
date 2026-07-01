"""
SQLite connection management for both chat history metadata and the
LangGraph checkpointer.
"""

import sqlite3

from app.core.config import get_settings

settings = get_settings()


class DatabaseManager:
    """Handles SQLite database creation and connections."""

    @staticmethod
    def initialize() -> None:
        """Create database and tables if they don't already exist."""
        settings.database_dir.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(settings.database_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_thread
                ON conversations(thread_id)
            """)
            conn.commit()

    @staticmethod
    def get_connection() -> sqlite3.Connection:
        """Return a new database connection."""
        settings.database_dir.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(settings.database_path, check_same_thread=False)


def initialize_database() -> None:
    DatabaseManager.initialize()
