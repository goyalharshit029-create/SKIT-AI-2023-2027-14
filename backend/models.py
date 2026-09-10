import enum
from datetime import date, datetime, timezone
from typing import Annotated, Any, Optional

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def _validate_object_id(value: Any) -> str:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, str) and ObjectId.is_valid(value):
        return value
    raise ValueError("Invalid ObjectId")


# Lets Mongo's ObjectId flow in/out of Pydantic models as a plain string.
PyObjectId = Annotated[str, BeforeValidator(_validate_object_id)]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    admin = "admin"
    doctor = "doctor"
    patient = "patient"
    lab_technician = "lab_technician"


class User(BaseModel):
    """Document shape for the `users` collection."""

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    full_name: str
    email: str
    password_hash: str
    role: UserRole
    is_active: bool = True
    created_at: datetime = Field(default_factory=utcnow)


class PatientProfile(BaseModel):
    """Document shape for the `patient_profiles` collection. `user_id` stores the
    referenced User's _id as a string (Mongo has no enforced foreign keys)."""

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    user_id: PyObjectId
    date_of_birth: Optional[date] = None
    sex: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    emergency_contact: Optional[str] = None
    updated_at: datetime = Field(default_factory=utcnow)


class HealthProfile(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    patient_id: PyObjectId
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    smoker: bool = False
    diabetes: bool = False
    hypertension: bool = False
    family_history: Optional[str] = None
    known_conditions: Optional[str] = None
    current_medications: Optional[str] = None
    updated_at: datetime = Field(default_factory=utcnow)


class MedicalDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    patient_id: PyObjectId
    document_type: str
    original_name: str
    stored_name: str
    content_type: Optional[str] = None
    size_bytes: int
    storage_path: str
    processing_status: str = "uploaded"
    processing_message: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=utcnow)


class ClinicalRecord(BaseModel):
    """Tabular clinical/lab features used to train the clinical-side prediction model."""

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    patient_id: PyObjectId
    age: Optional[int] = None
    resting_bp: Optional[int] = None
    cholesterol: Optional[int] = None
    fasting_blood_sugar: Optional[bool] = None
    max_heart_rate: Optional[int] = None
    exercise_angina: Optional[bool] = None
    recorded_at: datetime = Field(default_factory=utcnow)


class ECGRecording(BaseModel):
    """Metadata for an uploaded ECG recording. The raw waveform is stored as a file
    (via MedicalDocument / storage_path), not as rows/fields in MongoDB."""

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    patient_id: PyObjectId
    document_id: Optional[PyObjectId] = None
    sampling_rate_hz: int = 500
    lead_count: int = 1
    duration_seconds: Optional[float] = None
    signal_storage_path: str
    recorded_at: datetime = Field(default_factory=utcnow)
