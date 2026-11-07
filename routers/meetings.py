
import html
from fastapi.responses import HTMLResponse
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from pydantic import BaseModel, Field
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from database import SessionLocal
from models import Meeting
from models import Meeting, MeetingQuestion
from transcription_service import (
    extract_audio,
    transcribe_audio,
    transcribe_question_audio,
    download_google_drive_video,
)
from document_service import extract_document_text
from summary_service import generate_summary
from report_service import generate_pdf_report, generate_docx_report
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/meetings", tags=["Meetings"])

def get_user_upload_dir(user_id: int) -> Path:
    user_upload_dir = Path("uploads") / f"user_{user_id}"
    user_upload_dir.mkdir(parents=True, exist_ok=True)
    return user_upload_dir

class MeetingLinkRequest(BaseModel):
    url: str
    input_type: str
class RenameMeetingRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)

@router.post("/transcribe-link")
async def transcribe_meeting_link(
    request: MeetingLinkRequest,
    session_request: Request,
):
    user_id = session_request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Please log in to process a meeting.",
        )

    if request.input_type not in {"youtube", "meeting"}:
        raise HTTPException(
            status_code=400,
            detail="Input type must be 'youtube' or 'meeting'.",
        )

    parsed = urlparse(request.url.strip())
    host = (parsed.hostname or "").lower()

    youtube_hosts = {
        "youtube.com", "www.youtube.com", "m.youtube.com",
        "youtu.be", "www.youtube-nocookie.com",
    }
    drive_hosts = {"drive.google.com", "docs.google.com"}
    google_meet_hosts = {"meet.google.com"}
    zoom_hosts = {"zoom.us", "www.zoom.us", "app.zoom.us"}
    teams_hosts = {"teams.microsoft.com", "teams.live.com"}

    is_youtube = host in youtube_hosts
    is_drive = host in drive_hosts
    is_google_meet = host in google_meet_hosts
    is_zoom = host in zoom_hosts or host.endswith(".zoom.us")
    is_teams = (
        host in teams_hosts
        or host.endswith(".teams.microsoft.com")
        or host.endswith(".teams.live.com")
    )

    if parsed.scheme != "https" or not parsed.hostname:
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid HTTPS meeting URL.",
        )

    if not any([is_youtube, is_drive, is_google_meet, is_zoom, is_teams]):
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported URL. Use YouTube, Google Drive, "
                "Google Meet, Zoom, or Microsoft Teams."
            ),
        )

    if request.input_type == "youtube" and not is_youtube:
        raise HTTPException(
            status_code=400,
            detail="Please provide a YouTube URL.",
        )

    if request.input_type == "meeting" and is_youtube:
        raise HTTPException(
            status_code=400,
            detail="Select the YouTube option for YouTube URLs.",
        )

    if is_google_meet or is_zoom or is_teams:
        raise HTTPException(
            status_code=400,
            detail=(
                "This is a meeting-platform link, not a direct recording. "
                "Export or download the meeting recording, then upload the "
                "video file or provide an accessible recording URL."
            ),
        )

    db = SessionLocal()
    audio_path = None

    try:
        upload_dir = get_user_upload_dir(user_id)

        existing_ids = db.query(Meeting.id).filter(
            Meeting.id.like("MTG%")
        ).all()
        numbers = [
            int(row[0][3:])
            for row in existing_ids
            if row[0][3:].isdigit()
        ]
        meeting_id = f"MTG{max(numbers, default=0) + 1:03d}"

        video_path = upload_dir / f"{meeting_id}.mp4"
        audio_path = upload_dir / f"{meeting_id}.mp3"

        if is_youtube:
            result = subprocess.run(
                [
                    "yt-dlp", "--no-playlist", "--max-filesize", "500M",
                    "--merge-output-format", "mp4", "-f",
                    "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                    "-o", str(video_path), request.url,
                ],
                capture_output=True,
                text=True,
                timeout=600,
                check=False,
            )

            if result.returncode != 0 or not video_path.exists():
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Could not download this YouTube video. "
                        "It may be private, restricted, or unavailable."
                    ),
                )
            source_name = "YouTube"
        else:
            download_google_drive_video(request.url, video_path)
            source_name = "GoogleDrive"

        extract_audio(video_path, audio_path)
        transcript = transcribe_audio(audio_path)
        summary = generate_summary(transcript.get("text", ""))

        meeting = Meeting(
            id=meeting_id,
            user_id=user_id,
            filename=f"{source_name}_{meeting_id}.mp4",
            video_path=str(video_path),
            duration=transcript.get("duration", 0),
            transcript_text=transcript.get("text", ""),
            transcript_segments=transcript.get("segments", []),
            summary=summary,
            status="completed",
        )
        db.add(meeting)
        db.commit()

        return {
            "meeting_id": meeting_id,
            "filename": meeting.filename,
            "transcript": transcript,
            "summary": summary,
            "saved_to_database": True,
        }

    except HTTPException:
        db.rollback()
        raise
    except subprocess.TimeoutExpired as error:
        db.rollback()
        raise HTTPException(
            status_code=408,
            detail="Video download timed out. Try a shorter video.",
        ) from error
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Meeting-link processing failed: {error}",
        ) from error
    finally:
        db.close()
        if audio_path is not None:
            audio_path.unlink(missing_ok=True)

@router.post("/transcribe")
async def transcribe_meeting(
    request: Request,
    file: UploadFile = File(...),
):
    allowed_extensions = {
        # Video formats
        ".mp4", ".webm", ".mov", ".mkv", ".avi", ".m4v",

        # Audio formats
        ".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"
    }

    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Please log in to process a meeting.",
        )

    extension = Path(file.filename or "").suffix.lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Upload a supported audio or video file.",
        )

    db = SessionLocal()
    audio_path = None

    try:
        last_meeting = db.query(Meeting.id).filter(
            Meeting.id.like("MTG%")
        ).all()

        numbers = [
            int(row[0][3:])
            for row in last_meeting
            if row[0][3:].isdigit()
        ]

        next_number = max(numbers, default=0) + 1
        meeting_id = f"MTG{next_number:03d}"

        upload_dir = get_user_upload_dir(user_id)

        video_path = upload_dir / f"{meeting_id}{extension}"
        audio_path = upload_dir / f"{meeting_id}.mp3"

        with video_path.open("wb") as destination:
            shutil.copyfileobj(file.file, destination)

        if extension in {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"}:
            audio_path = video_path
        else:
            extract_audio(video_path, audio_path)

        transcript = transcribe_audio(audio_path)
        summary = generate_summary(transcript.get("text", ""))

        meeting = Meeting(
            id=meeting_id,
            user_id=user_id,
            filename=file.filename or "meeting",
            video_path=str(video_path),
            duration=transcript.get("duration", 0),
            transcript_text=transcript.get("text", ""),
            transcript_segments=transcript.get("segments", []),
            summary=summary,
            status="completed",
        )

        db.add(meeting)
        db.commit()

        return {
            "meeting_id": meeting_id,
            "filename": file.filename,
            "transcript": transcript,
            "summary": summary,
            "saved_to_database": True,
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Meeting transcription failed: {error}",
        ) from error

    finally:
        db.close()
        await file.close()

        if audio_path is not None and audio_path != video_path:
            audio_path.unlink(missing_ok=True)

@router.post("/documents")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Please log in to upload a document.",
        )

    extension = Path(file.filename or "").suffix.lower()

    if extension not in {".pdf", ".docx"}:
        raise HTTPException(
            status_code=400,
            detail="Upload a PDF or DOCX document.",
        )

    db = SessionLocal()
    document_path = None

    try:
        last_meeting = db.query(Meeting.id).filter(
            Meeting.id.like("MTG%")
        ).all()

        numbers = [
            int(row[0][3:])
            for row in last_meeting
            if row[0][3:].isdigit()
        ]

        meeting_id = f"MTG{max(numbers, default=0) + 1:03d}"

        upload_dir = get_user_upload_dir(user_id)

        document_path = upload_dir / f"{meeting_id}{extension}"

        with document_path.open("wb") as destination:
            shutil.copyfileobj(file.file, destination)

        document_text = extract_document_text(str(document_path))

        summary = generate_summary(document_text)

        meeting = Meeting(
            id=meeting_id,
            user_id=user_id,
            filename=file.filename or "document",
            video_path=str(document_path),
            duration=0,
            transcript_text=document_text,
            transcript_segments=[],
            summary=summary,
            status="completed",
        )

        db.add(meeting)
        db.commit()

        return {
            "meeting_id": meeting_id,
            "filename": file.filename,
            "input_type": "document",
            "summary": summary,
            "saved_to_database": True,
        }

    except ValueError as error:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {error}",
        ) from error

    finally:
        db.close()
        await file.close()

@router.get("")
def get_all_meetings(request: Request):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Please log in to view meeting history.",
        )

    db = SessionLocal()

    try:
        meetings = db.query(Meeting).filter(
            Meeting.user_id == user_id
        ).order_by(
            Meeting.id.desc()
        ).all()

        return {
            "meetings": [
                {
                    "meeting_id": meeting.id,
                    "filename": meeting.filename,
                    "duration": meeting.duration,
                    "status": meeting.status,
                    "created_at": (
                        meeting.created_at.isoformat()
                        if meeting.created_at
                        else None
                    ),
                }
                for meeting in meetings
            ]
        }

    finally:
        db.close()

@router.patch("/{meeting_id}/rename")
def rename_meeting(
    meeting_id: str,
    request: RenameMeetingRequest,
    session_request: Request,
):
    user_id = session_request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Please log in to rename this meeting.",
        )

    new_filename = request.filename.strip()

    if not new_filename:
        raise HTTPException(
            status_code=400,
            detail="Meeting name cannot be empty.",
        )

    db = SessionLocal()

    try:
        meeting = db.query(Meeting).filter(
            Meeting.id == meeting_id,
            Meeting.user_id == user_id,
        ).first()

        if meeting is None:
            raise HTTPException(
                status_code=404,
                detail="Meeting not found.",
            )

        meeting.filename = new_filename
        db.commit()
        db.refresh(meeting)

        return {
            "message": "Meeting renamed successfully.",
            "meeting_id": meeting.id,
            "filename": meeting.filename,
        }

    except HTTPException:
        raise

    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to rename meeting.",
        ) from error

    finally:
        db.close()

@router.get("/{meeting_id}")
def get_meeting(meeting_id: str, request: Request):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Please log in to view this meeting.",
        )

    db = SessionLocal()

    try:
        meeting = db.query(Meeting).filter(
            Meeting.id == meeting_id,
            Meeting.user_id == user_id,
        ).first()

        if meeting is None:
            raise HTTPException(
                status_code=404,
                detail="Meeting not found.",
            )

        return {
            "meeting_id": meeting.id,
            "filename": meeting.filename,
            "duration": meeting.duration,
            "transcript": meeting.transcript_text,
            "segments": meeting.transcript_segments,
            "summary": meeting.summary,
            "status": meeting.status,
        }

    finally:
        db.close()

@router.get("/{meeting_id}/video")
def get_meeting_video(meeting_id: str, request: Request):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Please log in to view this media file.",
        )

    db = SessionLocal()

    try:
        meeting = db.query(Meeting).filter(
            Meeting.id == meeting_id,
            Meeting.user_id == user_id,
        ).first()

        if meeting is None:
            raise HTTPException(
                status_code=404,
                detail="Meeting not found.",
            )

        original_path = Path(meeting.video_path)

        if not original_path.is_file():
            raise HTTPException(
                status_code=404,
                detail="Media file not found.",
            )

        extension = original_path.suffix.lower()

        # PDF documents can be displayed directly in the iframe.
        if extension == ".pdf":
            return FileResponse(
                path=original_path,
                media_type="application/pdf",
                content_disposition_type="inline",
            )

        # DOCX files are not reliably rendered by browser iframes.
        if extension == ".docx":
            document_text = extract_document_text(str(original_path))
            safe_text = html.escape(document_text)

            preview_html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Document Preview</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.7;
                        color: #1f2937;
                        padding: 24px;
                        margin: 0;
                        background: #ffffff;
                        overflow-wrap: anywhere;
                    }}
                    pre {{
                        white-space: pre-wrap;
                        font-family: inherit;
                        margin: 0;
                    }}
                </style>
            </head>
            <body>
                <pre>{safe_text}</pre>
            </body>
            </html>
            """

            return HTMLResponse(content=preview_html)

        audio_types = {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".m4a": "audio/mp4",
            ".ogg": "audio/ogg",
            ".flac": "audio/flac",
            ".aac": "audio/aac",
        }

        if extension in audio_types:
            media_path = original_path
            media_type = audio_types[extension]

        else:
            mp4_path = original_path.with_suffix(".mp4")
            media_path = (
                mp4_path if mp4_path.is_file() else original_path
            )

            video_types = {
                ".mp4": "video/mp4",
                ".webm": "video/webm",
                ".mov": "video/quicktime",
                ".mkv": "video/x-matroska",
                ".avi": "video/x-msvideo",
                ".m4v": "video/x-m4v",
            }

            media_type = video_types.get(
                media_path.suffix.lower(),
                "application/octet-stream",
            )

        return FileResponse(
            path=media_path,
            media_type=media_type,
            content_disposition_type="inline",
        )

    finally:
        db.close()

@router.delete("/{meeting_id}")
def delete_meeting(meeting_id: str, request: Request):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Please log in to delete a meeting.",
        )

    db = SessionLocal()

    try:
        meeting = db.query(Meeting).filter(
            Meeting.id == meeting_id,
            Meeting.user_id == user_id,
        ).first()

        if meeting is None:
            raise HTTPException(
                status_code=404,
                detail="Meeting not found.",
            )

        video_path = Path(meeting.video_path)
        mp4_path = video_path.with_suffix(".mp4")

        db.query(MeetingQuestion).filter(
            MeetingQuestion.meeting_id == meeting_id
        ).delete(synchronize_session=False)

        db.delete(meeting)
        db.commit()

        for path in {video_path, mp4_path}:
            if path.is_file():
                path.unlink()

        return {
            "message": "Meeting deleted successfully.",
            "meeting_id": meeting_id,
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete meeting: {error}",
        ) from error

    finally:
        db.close()


@router.get("/{meeting_id}/report/pdf")
def download_meeting_pdf(
    meeting_id: str,
    request: Request,
):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Please log in to download this report.",
        )

    db = SessionLocal()

    try:
        meeting = db.query(Meeting).filter(
            Meeting.id == meeting_id,
            Meeting.user_id == user_id,
        ).first()

        if meeting is None:
            raise HTTPException(
                status_code=404,
                detail="Meeting not found.",
            )

        pdf_buffer = generate_pdf_report(meeting)

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{meeting_id}_report.pdf"'
                )
            },
        )

    finally:
        db.close()


@router.get("/{meeting_id}/report/docx")
def download_meeting_docx(
    meeting_id: str,
    request: Request,
):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Please log in to download this report.",
        )

    db = SessionLocal()

    try:
        meeting = db.query(Meeting).filter(
            Meeting.id == meeting_id,
            Meeting.user_id == user_id,
        ).first()

        if meeting is None:
            raise HTTPException(
                status_code=404,
                detail="Meeting not found.",
            )

        docx_buffer = generate_docx_report(meeting)

        return StreamingResponse(
            docx_buffer,
            media_type=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{meeting_id}_report.docx"'
                )
            },
        )

    finally:
        db.close()


@router.post("/transcribe-question-audio")
async def transcribe_question_audio_endpoint(
    audio: UploadFile = File(...),
):
    if not audio.content_type or not audio.content_type.startswith("audio/"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a valid audio recording.",
        )

    suffix = Path(audio.filename or "question.webm").suffix or ".webm"
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            shutil.copyfileobj(audio.file, temp_file)

        question = transcribe_question_audio(temp_path)

        if not question:
            raise HTTPException(
                status_code=422,
                detail="No speech was detected. Please try again.",
            )

        return {"question": question}

    except HTTPException:
        raise
    except Exception as exc:
        print(f"Question audio transcription failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Could not transcribe the recording. Please try again.",
        )
    finally:
        await audio.close()
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)
