import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from pwdlib import PasswordHash


load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET or JWT_SECRET == "REPLACE_WITH_A_LONG_RANDOM_SECRET":
    raise RuntimeError("JWT_SECRET is missing or has not been changed in backend/.env.")

ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 60
password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(user_id: str, role: str) -> tuple[str, datetime]:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    token = jwt.encode(
        {"sub": user_id, "role": role, "exp": expires_at},
        JWT_SECRET,
        algorithm=ALGORITHM,
    )
    return token, expires_at


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
