from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.database import get_db

app = FastAPI()

@app.get("/test-db")
def test_db(db: Session = Depends(get_db)):
    return {"status": "connected"}
