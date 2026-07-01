from langgraph.checkpoint.sqlite import SqliteSaver

from app.database.database import DatabaseManager

conn = DatabaseManager.get_connection()
checkpointer = SqliteSaver(conn)
