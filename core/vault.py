import sqlite3
import os
import datetime

DB_PATH = os.path.join(os.path.expanduser("~"), ".peirro_vault.db")

class Vault:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    role TEXT,
                    content TEXT,
                    action_taken TEXT
                )
            """)

    def log(self, role: str, content: str, action: str = None):
        with self.conn:
            self.conn.execute(
                "INSERT INTO interactions (timestamp, role, content, action_taken) VALUES (?, ?, ?, ?)",
                (datetime.datetime.now().isoformat(), role, content, action)
            )
