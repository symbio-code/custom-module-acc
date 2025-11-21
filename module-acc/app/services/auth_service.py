from sqlmodel import Session, select
from fastapi import HTTPException
from app.models.user import AppUser
from app.utils.security import verify_password, hash_password

def init_superuser(db: Session, password: str):
    """Inisialisasi user pertama (jalankan sekali saja)"""
    existing_user = db.exec(select(AppUser)).first()
    if existing_user:
        return existing_user
    
    # Buat user baru
    user = AppUser(password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def authenticate(db: Session, password: str):
    """Autentikasi user dengan password"""
    user = db.exec(select(AppUser)).first()
    if not user:
        raise HTTPException(404, "User not registered")

    if not verify_password(password, user.password_hash):
        raise HTTPException(401, "Wrong password")

    return user