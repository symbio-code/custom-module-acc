from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session
import os

from app.database import get_session, init_db

from app.routers.account import router as account_router
from app.routers.journal import router as journal_router
from app.routers.ledger import router as ledger_router
from app.routers.auth import router as auth_router
from app.routers.frontend_auth import router as frontend_router


app = FastAPI()


# ----------------------------------------------------
# STARTUP: init database (SQLModel auto create table)
# ----------------------------------------------------
@app.on_event("startup")
def startup_event():
    init_db()


# ----------------------------------------------------
# TEST DB CONNECTION
# ----------------------------------------------------
@app.get("/test-db")
def test_db(db: Session = Depends(get_session)):
    return {"status": "connected"}


# ----------------------------------------------------
# HOME ROUTE
# ----------------------------------------------------
@app.get("/")
def home():
    return {"status": "running"}


# ----------------------------------------------------
# REGISTER ROUTERS
# ----------------------------------------------------
app.include_router(account_router)
app.include_router(journal_router)
app.include_router(ledger_router)
app.include_router(auth_router)
app.include_router(frontend_router)

# Serve static files from frontend/static if the folder exists
if os.path.isdir("frontend/static"):
    app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
