import os

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "cardioxai")

if not MONGODB_URI:
    raise RuntimeError(
        "MONGODB_URI is missing. Copy backend/.env.example to backend/.env "
        "and enter your MongoDB connection string."
    )

client: MongoClient = MongoClient(MONGODB_URI)
database: Database = client[MONGODB_DB_NAME]


def get_db() -> Database:
    """FastAPI dependency — yields the MongoDB database handle."""
    return database


def init_indexes() -> None:
    """Create indexes needed for correctness/performance. Call once on startup."""
    database["users"].create_index("email", unique=True)
    database["patient_profiles"].create_index("user_id", unique=True)
    database["health_profiles"].create_index("patient_id", unique=True)
    database["medical_documents"].create_index("patient_id")
    database["medical_documents"].create_index("stored_name", unique=True)
    database["clinical_records"].create_index("patient_id")
    database["ecg_recordings"].create_index("patient_id")
