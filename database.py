
import os
from pathlib import Path
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker


# DATABASE CONFIGURATION

DATABASE_DIR = Path("data")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./data/meetings.db",
)

db_url = make_url(DATABASE_URL)

connect_args = {}

if db_url.get_backend_name() == "sqlite":
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False}

else:
    if db_url.drivername in ("postgresql", "postgres"):
        db_url = db_url.set(
            drivername="postgresql+psycopg"
        )

    if "sslmode" not in db_url.query:
        db_url = db_url.update_query_dict(
            {"sslmode": "require"}
        )


engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

Base = declarative_base()


# USER MODEL

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


# MEETING MODEL

class Meeting(Base):
    __tablename__ = "meetings"

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    video_path = Column(String, nullable=False)
    duration = Column(Float, nullable=True)
    transcript_text = Column(Text, nullable=True)
    transcript_segments = Column(JSON, nullable=True)
    summary = Column(JSON, nullable=True)
    status = Column(String, default="uploaded", nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


# MEETING QUESTION MODEL

class MeetingQuestion(Base):
    __tablename__ = "meeting_questions"

    id = Column(Integer, primary_key=True, index=True)

    meeting_id = Column(
        String,
        ForeignKey("meetings.id"),
        nullable=False,
        index=True,
    )

    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


# DATABASE INITIALIZATION

def init_db():
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)

    meeting_columns = {
        column["name"]
        for column in inspector.get_columns("meetings")
    }

    if "user_id" not in meeting_columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE meetings "
                    "ADD COLUMN user_id INTEGER REFERENCES users(id)"
                )
            )

        print("Added user_id column to meetings table.")
