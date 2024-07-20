# main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.requests import Request
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer
from sqlalchemy import create_engine
from pydantic import BaseModel
from typing import Optional
import secrets
import validators
from starlette.datastructures import URL

app = FastAPI()

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///urls.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
Base = declarative_base()

class URL(Base):
    __tablename__ = "urls"
    id = Column(Integer, primary_key=True)
    target_url = Column(String, nullable=False)
    key = Column(String, nullable=False, unique=True)
    secret_key = Column(String, nullable=False, unique=True)

Base.metadata.create_all(bind=engine)

class URLBase(BaseModel):
    target_url: str

class URLInfo(URLBase):
    url: str
    admin_url: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_unique_random_key(db: Session) -> str:
    key = create_random_key()
    while db.query(URL).filter_by(key=key).first():
        key = create_random_key()
    return key

def create_random_key() -> str:
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return "".join(secrets.choice(chars) for _ in range(5))

@app.post("/url", response_model=URLInfo)
def create_url(url: URLBase, db: Session = Depends(get_db)):
    if not validators.url(url.target_url):
        raise HTTPException(status_code=400, detail="Invalid URL")
    key = create_unique_random_key(db)
    secret_key = create_unique_random_key(db)
    db_url = URL(target_url=url.target_url, key=key, secret_key=secret_key)
    db.add(db_url)
    db.commit()
    db.refresh(db_url)
    base_url = URL(get_settings().base_url)
    db_url.url = str(base_url.replace(path=db_url.key))
    db_url.admin_url = str(base_url.replace(path=f"admin/{db_url.secret_key}"))
    return db_url

@app.get("/{key}")
def redirect_to_target_url(key: str, db: Session = Depends(get_db)):
    if db_url := db.query(URL).filter_by(key=key).first():
        return RedirectResponse(url=db_url.target_url)
    else:
        raise HTTPException(status_code=404, detail="URL not found")

@app.get("/admin/{secret_key}", name="administration info", response_model=URLInfo)
def get_url_info(secret_key: str, request: Request, db: Session = Depends(get_db)):
    if db_url := db.query(URL).filter_by(secret_key=secret_key).first():
        base_url = URL(get_settings().base_url)
        db_url.url = str(base_url.replace(path=db_url.key))
        db_url.admin_url = str(base_url.replace(path=f"admin/{db_url.secret_key}"))
        return db_url
    else:
        raise HTTPException(status_code=404, detail="URL not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
    
 #   You can run the application using uvicorn by executing the following command:
#uvicorn main:app --host 0.0.0.0 --port 8000

#This will start the application on http://localhost:8000. You can then use a tool like curl to test the endpoints:
#curl -X POST -H "Content-Type: application/json" -d '{"target_url": "https://www.example.com"}' http://localhost:8000/url

#This should return a JSON response with the shortened URL and administration URL. You can then use the shortened URL to redirect to the target URL:
#curl http://localhost:8000/<shortened_url_key>
#This should redirect you to the target URL.

