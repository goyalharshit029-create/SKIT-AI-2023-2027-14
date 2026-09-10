import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Literal

import jwt
from bson import ObjectId
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from pymongo.database import Database

from database import get_db, init_indexes
from models import (
    HealthProfile,
    MedicalDocument,
    PatientProfile,
    User,
    UserRole,
    utcnow,
)
from security import create_access_token, decode_access_token, hash_password, verify_password


app = FastAPI(title="CardioXAI API", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOADS_DIR = Path(__file__).resolve().parent / "uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_TYPES = {
    "medical_report": {".pdf", ".png", ".jpg", ".jpeg"},
    "prescription": {".pdf", ".png", ".jpg", ".jpeg"},
    "ecg_data": {".csv", ".txt", ".dat", ".hea"},
    "ecg_report": {".pdf", ".png", ".jpg", ".jpeg"},
}
Role = Literal["admin", "doctor", "patient", "lab_technician"]
bearer_scheme = HTTPBearer()


# ── Request / Response schemas ──────────────────────────────────────


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: Role


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_at: datetime
    user: UserResponse


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class MessageResponse(BaseModel):
    message: str


class ProfileInput(BaseModel):
    date_of_birth: date | None = None
    sex: str | None = Field(default=None, max_length=20)
    phone: str | None = Field(default=None, max_length=30)
    city: str | None = Field(default=None, max_length=100)
    emergency_contact: str | None = Field(default=None, max_length=150)


class HealthInput(BaseModel):
    height_cm: float | None = Field(default=None, ge=30, le=300)
    weight_kg: float | None = Field(default=None, ge=1, le=500)
    smoker: bool = False
    diabetes: bool = False
    hypertension: bool = False
    family_history: str | None = Field(default=None, max_length=3000)
    known_conditions: str | None = Field(default=None, max_length=3000)
    current_medications: str | None = Field(default=None, max_length=3000)


# ── Helpers ─────────────────────────────────────────────────────────


def _oid(value: str) -> ObjectId:
    """Convert a string to a BSON ObjectId, raising 400 on failure."""
    try:
        return ObjectId(value)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format.")


def profile_payload(doc: dict | None) -> dict:
    if not doc:
        return {"date_of_birth": None, "sex": None, "phone": None, "city": None, "emergency_contact": None}
    return {
        "date_of_birth": doc.get("date_of_birth"),
        "sex": doc.get("sex"),
        "phone": doc.get("phone"),
        "city": doc.get("city"),
        "emergency_contact": doc.get("emergency_contact"),
    }


def health_payload(doc: dict | None) -> dict:
    if not doc:
        return {
            "height_cm": None, "weight_kg": None, "smoker": False,
            "diabetes": False, "hypertension": False, "family_history": None,
            "known_conditions": None, "current_medications": None,
        }
    return {
        "height_cm": float(doc["height_cm"]) if doc.get("height_cm") is not None else None,
        "weight_kg": float(doc["weight_kg"]) if doc.get("weight_kg") is not None else None,
        "smoker": doc.get("smoker", False),
        "diabetes": doc.get("diabetes", False),
        "hypertension": doc.get("hypertension", False),
        "family_history": doc.get("family_history"),
        "known_conditions": doc.get("known_conditions"),
        "current_medications": doc.get("current_medications"),
    }


def document_payload(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "document_type": doc["document_type"],
        "original_name": doc["original_name"],
        "content_type": doc.get("content_type"),
        "size_bytes": doc["size_bytes"],
        "processing_status": doc.get("processing_status", "uploaded"),
        "processing_message": doc.get("processing_message"),
        "uploaded_at": doc.get("uploaded_at"),
    }


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Database = Depends(get_db),
) -> dict:
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = ObjectId(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session.")
    user = db["users"].find_one({"_id": user_id})
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or inactive account.")
    return user


def require_patient(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != UserRole.patient.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Patient access is required.")
    return user


# ── Startup ─────────────────────────────────────────────────────────


@app.on_event("startup")
def on_startup() -> None:
    init_indexes()
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


# ── Routes ──────────────────────────────────────────────────────────


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def register_patient(registration: RegisterRequest, db: Database = Depends(get_db)) -> MessageResponse:
    email = registration.email.lower()
    if db["users"].find_one({"email": email}):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account already exists with this email address.")
    user = User(
        full_name=registration.full_name.strip(),
        email=email,
        password_hash=hash_password(registration.password),
        role=UserRole.patient,
    )
    db["users"].insert_one(user.model_dump(by_alias=True, exclude={"id"}))
    return MessageResponse(message="Account created. You can now sign in.")


@app.post("/api/auth/login", response_model=LoginResponse)
def login(credentials: LoginRequest, db: Database = Depends(get_db)) -> LoginResponse:
    user = db["users"].find_one({"email": credentials.email.lower()})
    if not user or not user.get("is_active", True) or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    access_token, expires_at = create_access_token(str(user["_id"]), user["role"])
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_at=expires_at,
        user=UserResponse(id=str(user["_id"]), name=user["full_name"], email=user["email"], role=user["role"]),
    )


@app.get("/api/patient/portal")
def get_patient_portal(patient: dict = Depends(require_patient), db: Database = Depends(get_db)) -> dict:
    patient_id = str(patient["_id"])
    profile = db["patient_profiles"].find_one({"user_id": patient_id})
    health = db["health_profiles"].find_one({"patient_id": patient_id})
    documents = list(db["medical_documents"].find({"patient_id": patient_id}).sort("uploaded_at", -1))
    return {
        "profile": profile_payload(profile),
        "health": health_payload(health),
        "documents": [document_payload(d) for d in documents],
    }


@app.put("/api/patient/profile", response_model=MessageResponse)
def save_patient_profile(
    data: ProfileInput,
    patient: dict = Depends(require_patient),
    db: Database = Depends(get_db),
) -> MessageResponse:
    patient_id = str(patient["_id"])
    update_data = data.model_dump()
    update_data["updated_at"] = utcnow()
    db["patient_profiles"].update_one(
        {"user_id": patient_id},
        {"$set": update_data, "$setOnInsert": {"user_id": patient_id}},
        upsert=True,
    )
    return MessageResponse(message="Personal profile saved.")


@app.put("/api/patient/health-profile", response_model=MessageResponse)
def save_health_profile(
    data: HealthInput,
    patient: dict = Depends(require_patient),
    db: Database = Depends(get_db),
) -> MessageResponse:
    patient_id = str(patient["_id"])
    update_data = data.model_dump()
    update_data["updated_at"] = utcnow()
    db["health_profiles"].update_one(
        {"patient_id": patient_id},
        {"$set": update_data, "$setOnInsert": {"patient_id": patient_id}},
        upsert=True,
    )
    return MessageResponse(message="Health profile saved.")


@app.post("/api/patient/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(
    document_type: str = Form(...),
    file: UploadFile = File(...),
    patient: dict = Depends(require_patient),
    db: Database = Depends(get_db),
) -> dict:
    if document_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document type.")
    original_name = Path(file.filename or "upload").name
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_TYPES[document_type]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This file type is not supported for the selected document category.")
    content = await file.read(MAX_FILE_SIZE + 1)
    if not content or len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be between 1 byte and 10 MB.")

    stored_name = f"{uuid.uuid4()}{suffix}"
    patient_id = str(patient["_id"])
    patient_folder = UPLOADS_DIR / patient_id
    patient_folder.mkdir(parents=True, exist_ok=True)
    destination = patient_folder / stored_name
    destination.write_bytes(content)

    category_message = (
        "Validated and ready for future ECG preprocessing."
        if document_type == "ecg_data"
        else "Validated and ready for secure clinical review."
    )
    doc = MedicalDocument(
        patient_id=patient_id,
        document_type=document_type,
        original_name=original_name,
        stored_name=stored_name,
        content_type=file.content_type,
        size_bytes=len(content),
        storage_path=str(destination),
        processing_status="validated",
        processing_message=category_message,
    )
    result = db["medical_documents"].insert_one(doc.model_dump(by_alias=True, exclude={"id"}))
    inserted = db["medical_documents"].find_one({"_id": result.inserted_id})
    return document_payload(inserted)


@app.get("/api/patient/documents/{document_id}/download")
def download_document(
    document_id: str,
    patient: dict = Depends(require_patient),
    db: Database = Depends(get_db),
) -> FileResponse:
    doc = db["medical_documents"].find_one({"_id": _oid(document_id)})
    if not doc or doc["patient_id"] != str(patient["_id"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    path = Path(doc["storage_path"])
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored file is unavailable.")
    return FileResponse(path, media_type=doc.get("content_type") or "application/octet-stream", filename=doc["original_name"])
