import hashlib
from pymongo import MongoClient
from src.core.config import MONGO_URI, DB_NAME, NOTIFICATIONS_COLLECTION, CHECKPOINTS_COLLECTION

class MongoHandler:
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[DB_NAME]
        self.notifications = self.db[NOTIFICATIONS_COLLECTION]
        self.checkpoints = self.db[CHECKPOINTS_COLLECTION]
        
        self.notifications.create_index("metadata.file_hash", unique=True)
        self.notifications.create_index("status")

    def generate_hash(self, file_bytes: bytes) -> str:
        return hashlib.sha256(file_bytes).hexdigest()

    def store_notification(self, endata: dict, metadata: dict, status: str = "completed"):
        """Saves the final EnData result wrapper."""
        payload = {
            "enData": endata,           # <-- This matches the NG UDM specs
            "metadata": metadata,       # <-- LangGraph processing tracking
            "status": status,           # <-- Required for Review UI
            "processed_at": metadata.get("processed_at")
        }
        try:
            self.notifications.insert_one(payload)
            return True
        except Exception as e:
            if "duplicate key error" in str(e):
                print("⚠️ File already exists in database. Skipping duplicate.")
            else:
                print(f"❌ Database Error: {e}")
            return False