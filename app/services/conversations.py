from app.database.database import DatabaseManager
import sqlite3

def save_message(thread_id: str, role: str, message: str):
    conn = DatabaseManager.get_connection()

    conn.execute(
        """
        INSERT INTO conversations(thread_id, role, message)
        VALUES (?, ?, ?)
        """,
        (thread_id, role, message),
    )

    conn.commit()
    conn.close()


def get_messages(thread_id: str):
    conn = DatabaseManager.get_connection()
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT role, message
        FROM conversations
        WHERE thread_id = ?
        ORDER BY created_at ASC
        """,
        (thread_id,),
    ).fetchall()

    conn.close()

    return [
        {
            "role": row["role"],
            "content": row["message"],
        }
        for row in rows
    ]

