import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Auto-load db/.env so DATABASE_URL is available without manual export
load_dotenv(Path(__file__).resolve().parents[2] / "db" / ".env")

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # Use psycopg v3 driver (not psycopg2) with SQLAlchemy
    SQLALCHEMY_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(SQLALCHEMY_URL, pool_pre_ping=True)
else:
    engine = None

SessionLocal = sessionmaker(bind=engine) if engine else None
