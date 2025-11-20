from fastapi import FastAPI, Depends
from sqlmodel import Session
from app.database import get_session, init_db

from app.routers.account import router as account_router
from app.routers.journal import router as journal_router
from app.routers.report import router as report_router


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
app.include_router(report_router)
