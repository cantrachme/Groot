import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)


DATABASE_URL = URL.create(
    "postgresql+psycopg",
    username=os.getenv("POSTGRES_USER", "rachit"),
    password=os.getenv("POSTGRES_PASSWORD", ""),
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=int(os.getenv("POSTGRES_PORT", "5432")),
    database=os.getenv("POSTGRES_DB", "groot_db"),
).render_as_string(hide_password=False)


# Create the SQLAlchemy engine for PostgreSQL.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base for model definitions
Base = declarative_base()
