
from pathlib import Path
from dotenv import load_dotenv
import hashlib
import mimetypes

load_dotenv()

from sqlalchemy import text
from database import SessionLocal, Meeting

PROJECT_DIR = Path(__file__).resolve().parent

db = SessionLocal()

try:
    # Find the smallest existing video/audio file
    meetings = db.query(Meeting).all()

    candidates = []

    allowed_extensions = {
        ".mp4", ".webm", ".mp3", ".wav", ".m4a", ".ogg"
    }

    for meeting in meetings:
        path = Path(meeting.video_path)

        if not path.is_absolute():
            path = PROJECT_DIR / path

        if (
            path.is_file()
            and path.suffix.lower() in allowed_extensions
        ):
            candidates.append((path.stat().st_size, meeting, path))

    if not candidates:
        raise RuntimeError("No existing video/audio files found.")

    candidates.sort(key=lambda item: item[0])

    file_size, meeting, file_path = candidates[0]

    print("Selected meeting:", meeting.id)
    print("Selected file:", file_path.name)
    print("Original size:", file_size, "bytes")

    # Read original file
    original_data = file_path.read_bytes()
    original_hash = hashlib.sha256(original_data).hexdigest()

    content_type = (
        mimetypes.guess_type(file_path.name)[0]
        or "application/octet-stream"
    )

    # Prevent duplicate test insertion
    existing = db.execute(
        text("""
            SELECT meeting_id
            FROM meeting_media
            WHERE meeting_id = :meeting_id
        """),
        {"meeting_id": meeting.id}
    ).first()

    if existing:
        raise RuntimeError(
            f"Media already exists for {meeting.id}. "
            "Test stopped without overwriting."
        )

    # Insert media into PostgreSQL
    db.execute(
        text("""
            INSERT INTO meeting_media (
                meeting_id,
                media_data,
                original_filename,
                content_type,
                file_size,
                sha256
            )
            VALUES (
                :meeting_id,
                :media_data,
                :filename,
                :content_type,
                :file_size,
                :sha256
            )
        """),
        {
            "meeting_id": meeting.id,
            "media_data": original_data,
            "filename": file_path.name,
            "content_type": content_type,
            "file_size": file_size,
            "sha256": original_hash
        }
    )

    # Read the file back from PostgreSQL
    result = db.execute(
        text("""
            SELECT media_data, file_size, sha256
            FROM meeting_media
            WHERE meeting_id = :meeting_id
        """),
        {"meeting_id": meeting.id}
    ).first()

    if not result:
        raise RuntimeError("Media retrieval failed.")

    retrieved_data = bytes(result.media_data)
    retrieved_hash = hashlib.sha256(retrieved_data).hexdigest()

    print("\n========== VERIFICATION ==========")
    print("Original size:", len(original_data))
    print("Retrieved size:", len(retrieved_data))
    print("Original SHA256:", original_hash)
    print("Retrieved SHA256:", retrieved_hash)

    if (
        original_hash != retrieved_hash
        or len(original_data) != result.file_size
    ):
        raise RuntimeError("Media verification failed.")

    db.commit()

    print("\nSUCCESS: Media stored and verified in Aiven!")

except Exception:
    db.rollback()
    raise

finally:
    db.close()
