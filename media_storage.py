
import hashlib
import mimetypes
from pathlib import Path

from sqlalchemy import text

from database import SessionLocal

CHUNK_SIZE = 1024 * 1024  # 1 MB


def store_media_file(db, meeting_id: str, file_path: Path):
    """Store a local file in Aiven BYTEA and verify it before commit."""

    file_path = Path(file_path)
    file_size = file_path.stat().st_size

    existing = db.execute(
        text("""
            SELECT 1
            FROM meeting_media
            WHERE meeting_id = :meeting_id
        """),
        {"meeting_id": meeting_id},
    ).first()

    if existing:
        raise RuntimeError(
            f"Media already exists for {meeting_id}; refusing to overwrite."
        )

    # Calculate the original file hash.
    original_hash = hashlib.sha256()

    with file_path.open("rb") as source:
        while chunk := source.read(CHUNK_SIZE):
            original_hash.update(chunk)

    original_hash = original_hash.hexdigest()

    # Create a temporary PostgreSQL large object.
    oid = db.execute(
        text("SELECT lo_create(0)")
    ).scalar_one()

    fd = None

    try:
        fd = db.execute(
            text("SELECT lo_open(:oid, 131072)"),
            {"oid": oid},
        ).scalar_one()

        uploaded = 0

        with file_path.open("rb") as source:
            while chunk := source.read(CHUNK_SIZE):
                written = db.execute(
                    text("SELECT lowrite(:fd, :chunk)"),
                    {"fd": fd, "chunk": chunk},
                ).scalar_one()

                if written != len(chunk):
                    raise RuntimeError(
                        f"Incomplete upload for {meeting_id}."
                    )

                uploaded += written

        if uploaded != file_size:
            raise RuntimeError("Uploaded file size does not match.")

        # Verify the large object before inserting it into BYTEA.
        db.execute(
            text("SELECT lo_lseek(:fd, 0, 0)"),
            {"fd": fd},
        )

        uploaded_hash = hashlib.sha256()
        retrieved = 0

        while True:
            chunk = db.execute(
                text("SELECT loread(:fd, :amount)"),
                {"fd": fd, "amount": CHUNK_SIZE},
            ).scalar_one()

            chunk = bytes(chunk)

            if not chunk:
                break

            uploaded_hash.update(chunk)
            retrieved += len(chunk)

        if retrieved != file_size:
            raise RuntimeError("Large-object size verification failed.")

        if uploaded_hash.hexdigest() != original_hash:
            raise RuntimeError("Large-object SHA-256 verification failed.")

        db.execute(
            text("SELECT lo_close(:fd)"),
            {"fd": fd},
        )
        fd = None

        content_type = (
            mimetypes.guess_type(file_path.name)[0]
            or "application/octet-stream"
        )

        # PostgreSQL converts the verified large object to BYTEA.
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
                    lo_get(:oid),
                    :filename,
                    :content_type,
                    :file_size,
                    :sha256
                )
            """),
            {
                "meeting_id": meeting_id,
                "oid": oid,
                "filename": file_path.name,
                "content_type": content_type,
                "file_size": file_size,
                "sha256": original_hash,
            },
        )

        # Verify the actual BYTEA value in chunks.
        stored_size = db.execute(
            text("""
                SELECT octet_length(media_data)
                FROM meeting_media
                WHERE meeting_id = :meeting_id
            """),
            {"meeting_id": meeting_id},
        ).scalar_one()

        if stored_size != file_size:
            raise RuntimeError("BYTEA size verification failed.")

        stored_hash = hashlib.sha256()
        offset = 1

        while offset <= file_size:
            chunk = db.execute(
                text("""
                    SELECT substring(
                        media_data FROM :start FOR :amount
                    )
                    FROM meeting_media
                    WHERE meeting_id = :meeting_id
                """),
                {
                    "start": offset,
                    "amount": CHUNK_SIZE,
                    "meeting_id": meeting_id,
                },
            ).scalar_one()

            chunk = bytes(chunk)

            if not chunk:
                raise RuntimeError("BYTEA verification returned incomplete data.")

            stored_hash.update(chunk)
            offset += len(chunk)

        if stored_hash.hexdigest() != original_hash:
            raise RuntimeError("BYTEA SHA-256 verification failed.")

        # Remove the temporary large object.
        db.execute(
            text("SELECT lo_unlink(:oid)"),
            {"oid": oid},
        )

        print(
            f"MEDIA VERIFIED: {meeting_id} | "
            f"{file_size} bytes | SHA256: {original_hash}"
        )

        return {
            "file_size": file_size,
            "sha256": original_hash,
            "content_type": content_type,
        }

    finally:
        if fd is not None:
            db.execute(
                text("SELECT lo_close(:fd)"),
                {"fd": fd},
            )


def iter_media_chunks(meeting_id: str, start: int, length: int):
    """Read a BYTEA range from Aiven in chunks; start is zero-based."""

    db = SessionLocal()

    try:
        offset = start
        remaining = length

        while remaining > 0:
            amount = min(CHUNK_SIZE, remaining)

            chunk = db.execute(
                text("""
                    SELECT substring(
                        media_data FROM :position FOR :amount
                    )
                    FROM meeting_media
                    WHERE meeting_id = :meeting_id
                """),
                {
                    "position": offset + 1,
                    "amount": amount,
                    "meeting_id": meeting_id,
                },
            ).scalar_one_or_none()

            if not chunk:
                break

            chunk = bytes(chunk)
            yield chunk

            offset += len(chunk)
            remaining -= len(chunk)

    finally:
        db.close()
