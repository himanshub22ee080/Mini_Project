import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Email Configuration
EMAIL_HOST = os.getenv("EMAIL_HOST", "imap.gmail.com")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

# Database Configuration
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "ExchangeSystem"
NOTIFICATIONS_COLLECTION = "notifications"
CHECKPOINTS_COLLECTION = "checkpoints"

# Path Configurations
INCOMING_DIR = "data/incoming"
ARCHIVE_DIR = "data/archive"

# Logic Settings
CONFIDENCE_THRESHOLD = 0.85  # Below this, status = 'pending_review'