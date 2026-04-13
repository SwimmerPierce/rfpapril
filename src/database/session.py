import os
from dotenv import load_dotenv
from sqlmodel import Session, create_engine, SQLModel
from . import models

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Default to sqlite for testing if no DB URL is provided
    DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(DATABASE_URL, echo=False)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

def get_engine():
    return engine
