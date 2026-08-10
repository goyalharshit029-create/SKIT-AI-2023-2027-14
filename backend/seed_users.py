"""Create local development accounts in PostgreSQL if they do not already exist."""

from sqlalchemy import select

from database import SessionLocal
from models import User, UserRole
from security import hash_password


DEVELOPMENT_USERS = [
    ("System Administrator", "admin@cardioxai.org", "Admin@123", UserRole.admin),
    ("Dr. Aditi Sharma", "doctor@cardioxai.org", "Doctor@123", UserRole.doctor),
    ("Rohan Mehta", "patient@cardioxai.org", "Patient@123", UserRole.patient),
    ("Arjun Singh", "lab@cardioxai.org", "Lab@123", UserRole.lab_technician),
]


def seed_users() -> None:
    with SessionLocal() as db:
        created = []
        for full_name, email, password, role in DEVELOPMENT_USERS:
            exists = db.scalar(select(User).where(User.email == email))
            if exists:
                print(f"Skipped existing user: {email}")
                continue

            db.add(
                User(
                    full_name=full_name,
                    email=email,
                    password_hash=hash_password(password),
                    role=role,
                )
            )
            created.append(email)
        db.commit()
        for email in created:
            print(f"Created: {email}")


if __name__ == "__main__":
    seed_users()
