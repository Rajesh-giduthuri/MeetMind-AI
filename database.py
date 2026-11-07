
from pathlib import Path

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
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime, timezone

DATABASE_DIR = Path("data")
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = "sqlite:///./data/meetings.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

Base = declarative_base()

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



def init_db():
    Base.metadata.create_all(bind=engine)

    from sqlalchemy import inspect, text

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

