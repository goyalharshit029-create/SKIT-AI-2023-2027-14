"""
MongoDB connection and initialization.

Uses the centralized `settings` object for connection details.
"""

from pymongo import MongoClient
from pymongo.database import Database

from config import settings

# ── Connection ───────────────────────────────────────────────────

client: MongoClient = MongoClient(settings.MONGODB_URI)
database: Database = client[settings.MONGODB_DB_NAME]


def get_db() -> Database:
    """FastAPI dependency — returns the MongoDB database handle."""
    return database


def init_indexes() -> None:
    """Create indexes needed for correctness and performance.

    Called once on application startup. Safe to call multiple times —
    MongoDB skips indexes that already exist.
    """
    database["users"].create_index("email", unique=True)
    database["patient_profiles"].create_index("user_id", unique=True)
    database["health_profiles"].create_index("patient_id", unique=True)
    database["medical_documents"].create_index("patient_id")
    database["medical_documents"].create_index("stored_name", unique=True)
    database["clinical_records"].create_index("patient_id")
    database["ecg_recordings"].create_index("patient_id")
    database["ecg_recordings"].create_index("stored_name", unique=True)
