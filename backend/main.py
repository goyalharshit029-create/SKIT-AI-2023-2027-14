import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Literal

import jwt
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import HealthProfile, MedicalDocument, PatientProfile, User, UserRole
from security import create_access_token, decode_access_token, hash_password, verify_password


app = FastAPI(title="CardioXAI API", version="0.3.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

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


def profile_payload(profile: PatientProfile | None) -> dict:
    if not profile:
        return {"date_of_birth": None, "sex": None, "phone": None, "city": None, "emergency_contact": None}
    return {"date_of_birth": profile.date_of_birth, "sex": profile.sex, "phone": profile.phone, "city": profile.city, "emergency_contact": profile.emergency_contact}


def health_payload(health: HealthProfile | None) -> dict:
    if not health:
        return {"height_cm": None, "weight_kg": None, "smoker": False, "diabetes": False, "hypertension": False, "family_history": None, "known_conditions": None, "current_medications": None}
    return {"height_cm": float(health.height_cm) if health.height_cm is not None else None, "weight_kg": float(health.weight_kg) if health.weight_kg is not None else None, "smoker": health.smoker, "diabetes": health.diabetes, "hypertension": health.hypertension, "family_history": health.family_history, "known_conditions": health.known_conditions, "current_medications": health.current_medications}


def document_payload(document: MedicalDocument) -> dict:
    return {"id": str(document.id), "document_type": document.document_type, "original_name": document.original_name, "content_type": document.content_type, "size_bytes": document.size_bytes, "processing_status": document.processing_status, "processing_message": document.processing_message, "uploaded_at": document.uploaded_at}


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session.")
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or inactive account.")
    return user


def require_patient(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.patient:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Patient access is required.")
    return user


@app.on_event("startup")
def create_portal_tables() -> None:
    # Creates missing portal tables only; it does not remove or overwrite existing data.
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE medical_documents ADD COLUMN IF NOT EXISTS processing_status VARCHAR(40) NOT NULL DEFAULT 'uploaded'"))
        connection.execute(text("ALTER TABLE medical_documents ADD COLUMN IF NOT EXISTS processing_message VARCHAR(300)"))
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def register_patient(registration: RegisterRequest, db: Session = Depends(get_db)) -> MessageResponse:
    email = registration.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account already exists with this email address.")
    db.add(User(full_name=registration.full_name.strip(), email=email, password_hash=hash_password(registration.password), role=UserRole.patient))
    db.commit()
    return MessageResponse(message="Account created. You can now sign in.")


@app.post("/api/auth/login", response_model=LoginResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.scalar(select(User).where(User.email == credentials.email.lower()))
    if not user or not user.is_active or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    access_token, expires_at = create_access_token(str(user.id), user.role.value)
    return LoginResponse(access_token=access_token, token_type="bearer", expires_at=expires_at, user=UserResponse(id=str(user.id), name=user.full_name, email=user.email, role=user.role.value))


@app.get("/api/patient/portal")
def get_patient_portal(patient: User = Depends(require_patient), db: Session = Depends(get_db)) -> dict:
    profile = db.get(PatientProfile, patient.id)
    health = db.scalar(select(HealthProfile).where(HealthProfile.patient_id == patient.id))
    documents = db.scalars(select(MedicalDocument).where(MedicalDocument.patient_id == patient.id).order_by(MedicalDocument.uploaded_at.desc())).all()
    return {"profile": profile_payload(profile), "health": health_payload(health), "documents": [document_payload(item) for item in documents]}


@app.put("/api/patient/profile", response_model=MessageResponse)
def save_patient_profile(data: ProfileInput, patient: User = Depends(require_patient), db: Session = Depends(get_db)) -> MessageResponse:
    profile = db.get(PatientProfile, patient.id)
    if not profile:
        profile = PatientProfile(user_id=patient.id)
        db.add(profile)
    for key, value in data.model_dump().items():
        setattr(profile, key, value)
    db.commit()
    return MessageResponse(message="Personal profile saved.")


@app.put("/api/patient/health-profile", response_model=MessageResponse)
def save_health_profile(data: HealthInput, patient: User = Depends(require_patient), db: Session = Depends(get_db)) -> MessageResponse:
    health = db.scalar(select(HealthProfile).where(HealthProfile.patient_id == patient.id))
    if not health:
        health = HealthProfile(patient_id=patient.id)
        db.add(health)
    for key, value in data.model_dump().items():
        setattr(health, key, value)
    db.commit()
    return MessageResponse(message="Health profile saved.")


@app.post("/api/patient/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(document_type: str = Form(...), file: UploadFile = File(...), patient: User = Depends(require_patient), db: Session = Depends(get_db)) -> dict:
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
    patient_folder = UPLOADS_DIR / str(patient.id)
    patient_folder.mkdir(parents=True, exist_ok=True)
    destination = patient_folder / stored_name
    destination.write_bytes(content)
    category_message = "Validated and ready for future ECG preprocessing." if document_type == "ecg_data" else "Validated and ready for secure clinical review."
    document = MedicalDocument(patient_id=patient.id, document_type=document_type, original_name=original_name, stored_name=stored_name, content_type=file.content_type, size_bytes=len(content), storage_path=str(destination), processing_status="validated", processing_message=category_message)
    db.add(document)
    db.commit()
    db.refresh(document)
    return document_payload(document)


@app.get("/api/patient/documents/{document_id}/download")
def download_document(document_id: uuid.UUID, patient: User = Depends(require_patient), db: Session = Depends(get_db)) -> FileResponse:
    document = db.get(MedicalDocument, document_id)
    if not document or document.patient_id != patient.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    path = Path(document.storage_path)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored file is unavailable.")
    return FileResponse(path, media_type=document.content_type or "application/octet-stream", filename=document.original_name)
