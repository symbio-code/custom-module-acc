from fastapi import APIRouter, Depends, Response
from sqlmodel import Session
from app.database import get_session
from app.services.auth_service import authenticate, init_superuser
from app.utils.session import create_session, destroy_session

router = APIRouter(prefix="/auth")

@router.post("/init")
def initialize_superuser(password: str, db: Session = Depends(get_session)):
    """Endpoint untuk inisialisasi user pertama (sekali saja)"""
    return init_superuser(db, password)

@router.post("/login")
def login(
    password: str, 
    response: Response, 
    db: Session = Depends(get_session)
):
    """Endpoint untuk login"""
    user = authenticate(db, password)
    create_session(response, user.id)
    return {"status": "logged_in"}

@router.post("/logout")
def logout(response: Response):
    """Endpoint untuk logout"""
    destroy_session(response)
    return {"status": "logged_out"}