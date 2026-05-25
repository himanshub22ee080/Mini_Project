import hashlib
from pymongo import MongoClient
from src.core.config import MONGO_URI, DB_NAME, NOTIFICATIONS_COLLECTION, CHECKPOINTS_COLLECTION

class MongoHandler:
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[DB_NAME]
        
        # Main collection for extracted exchange data
        self.notifications = self.db[NOTIFICATIONS_COLLECTION]
        
        # Collection for LangGraph state/checkpoints (Human-in-the-loop)
        self.checkpoints = self.db[CHECKPOINTS_COLLECTION]
        
        # Create a unique index on file_hash to prevent duplicate processing
        self.notifications.create_index("metadata.file_hash", unique=True)
        # Index on status for faster UI querying (Pending Review vs Completed)
        self.notifications.create_index("status")

    def generate_hash(self, file_bytes: bytes) -> str:
        """Generates a unique fingerprint for a file."""
        return hashlib.sha256(file_bytes).hexdigest()

    def store_notification(self, data: dict, metadata: dict, status: str = "completed"):
        """Saves the final extracted result to the notifications collection."""
        payload = {
            "extracted_fields": data,
            "metadata": metadata,
            "status": status,
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

    def save_checkpoint(self, thread_id: str, checkpoint_data: dict):
        """Used by LangGraph to save state for Human-in-the-Loop interruptions."""
        self.checkpoints.update_one(
            {"thread_id": thread_id},
            {"$set": checkpoint_data},
            upsert=True
        )