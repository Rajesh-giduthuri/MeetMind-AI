
import os
import subprocess
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

import re
import requests
from urllib.parse import urlparse
from fastapi import HTTPException
load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv(
    "GROQ_TRANSCRIPTION_MODEL",
    "whisper-large-v3",
)

CHUNK_SECONDS = 60
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

client = Groq(api_key=API_KEY) if API_KEY else None

def convert_video_to_mp4(input_path, output_path):
    """Convert an uploaded video to browser-compatible MP4."""
    command = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
        "-c:v", "libx264",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-movflags", "+faststart",
        str(output_path),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Video conversion failed: {result.stderr[-1500:]}"
        )

    return output_path

def extract_audio(video_path: Path, audio_path: Path) -> None:
    """Extract mono, 16 kHz audio from a video using FFmpeg."""
    command = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-c:a", "libmp3lame",
        "-b:a", "64k",
        str(audio_path),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "FFmpeg audio extraction failed: "
            + result.stderr[-1500:]
        )


def get_audio_duration(audio_path: Path) -> float:
    """Read audio duration using FFprobe."""
    command = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
    )

    return float(result.stdout.strip())


def transcribe_audio(audio_path: Path) -> dict:
    """Transcribe audio in one-minute chunks with absolute timestamps."""
    if client is None:
        raise RuntimeError("GROQ_API_KEY is missing from .env")

    duration = get_audio_duration(audio_path)
    all_segments = []

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        chunk_start = 0.0
        chunk_index = 0

        while chunk_start < duration:
            chunk_index += 1
            chunk_end = min(
                chunk_start + CHUNK_SECONDS,
                duration,
            )

            chunk_path = temp_path / f"chunk_{chunk_index}.mp3"

            command = [
                "ffmpeg",
                "-y",
                "-i", str(audio_path),
                "-ss", str(chunk_start),
                "-t", str(chunk_end - chunk_start),
                "-c:a", "libmp3lame",
                "-b:a", "64k",
                str(chunk_path),
            ]

            subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
            )

            with chunk_path.open("rb") as audio_file:
                result = client.audio.transcriptions.create(
                    file=(chunk_path.name, audio_file.read()),
                    model=MODEL,
                    language="en",
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                )


            for segment in result.segments or []:
            # Support both dictionary and object responses.
                if isinstance(segment, dict):
                    segment_text = segment.get("text", "")
                    segment_start = segment.get("start", 0)
                    segment_end = segment.get("end", 0)
                else:
                    segment_text = segment.text
                    segment_start = segment.start
                    segment_end = segment.end

                segment_text = segment_text.strip()

                if not segment_text:
                    continue

                all_segments.append({
                    "start": round(
                    chunk_start + float(segment_start), 3
                    ),
                    "end": round(
                    chunk_start + float(segment_end), 3
                    ),
                    "text": segment_text,
                })

            print(
                f"Transcribed chunk {chunk_index}: "
                f"{chunk_start:.0f}s–{chunk_end:.0f}s"
            )

            chunk_start = chunk_end

    return {
        "duration": round(duration, 3),
        "model": MODEL,
        "segments": all_segments,
        "text": " ".join(
            segment["text"] for segment in all_segments
        ),
    }

def download_google_drive_video(url: str, destination: Path) -> None:
    """Download an accessible Google Drive video with confirmation handling."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    allowed_hosts = {
        "drive.google.com",
        "docs.google.com",
    }

    if parsed.scheme != "https" or host not in allowed_hosts:
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid HTTPS Google Drive file URL.",
        )

    match = re.search(r"/file/d/([A-Za-z0-9_-]+)", parsed.path)

    if not match:
        raise HTTPException(
            status_code=400,
            detail="Could not find a Google Drive file ID in the URL.",
        )

    file_id = match.group(1)
    download_url = "https://drive.google.com/uc"

    with requests.Session() as session:
        response = session.get(
            download_url,
            params={"export": "download", "id": file_id},
            stream=True,
            timeout=(15, 120),
        )
        response.raise_for_status()

        content_type = response.headers.get(
            "Content-Type", ""
        ).lower()

        # Google Drive may return an HTML confirmation page for large files.
        if "text/html" in content_type:
            response.close()

            page_response = session.get(
                download_url,
                params={"export": "download", "id": file_id},
                timeout=(15, 120),
            )
            page_response.raise_for_status()

            token_match = re.search(
                r'confirm=([0-9A-Za-z_-]+)',
                page_response.text,
            )

            if not token_match:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Google Drive requires confirmation or access. "
                        "Check the sharing permissions; private files "
                        "require authenticated Google Drive access."
                    ),
                )

            response = session.get(
                download_url,
                params={
                    "export": "download",
                    "id": file_id,
                    "confirm": token_match.group(1),
                },
                stream=True,
                timeout=(15, 120),
            )
            response.raise_for_status()

            content_type = response.headers.get(
                "Content-Type", ""
            ).lower()

            if "text/html" in content_type:
                response.close()
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Google Drive did not return a video file. "
                        "The file may require authentication or "
                        "additional confirmation."
                    ),
                )

        try:
            total_bytes = 0
            max_bytes = 500 * 1024 * 1024

            with destination.open("wb") as output:
                for chunk in response.iter_content(
                    chunk_size=1024 * 1024
                ):
                    if not chunk:
                        continue

                    total_bytes += len(chunk)

                    if total_bytes > max_bytes:
                        raise HTTPException(
                            status_code=413,
                            detail="Google Drive video exceeds the 500 MB limit.",
                        )

                    output.write(chunk)
        finally:
            response.close()

    if not destination.exists() or destination.stat().st_size == 0:
        raise HTTPException(
            status_code=400,
            detail="The Google Drive video download was empty.",
        )


def transcribe_question_audio(audio_path: Path) -> str:
    """Transcribe speech and preserve English or Roman-script Hinglish."""
    if client is None:
        raise RuntimeError("GROQ_API_KEY is missing from .env")

    with audio_path.open("rb") as audio_file:
        result = client.audio.transcriptions.create(
            file=(audio_path.name, audio_file.read()),
            model=MODEL,
            response_format="text",
            language="hi",
        )

    if isinstance(result, str):
        transcript = result.strip()
    else:
        transcript = getattr(result, "text", "").strip()

    if not transcript:
        return ""

    # Keep English transcription unchanged when no Devanagari is present.
    if not any("\u0900" <= char <= "\u097F" for char in transcript):
        return transcript

    # Convert Hindi-script transcription to Roman-script Hinglish.
    chat_result = client.chat.completions.create(
        model=os.getenv("GROQ_CHAT_MODEL", "openai/gpt-oss-20b"),
        messages=[
            {
                "role": "system",
                "content": (
                    "Transliterate the Hindi transcription into natural "
                    "Roman-script Hindi/Hinglish. Preserve English technical "
                    "terms and names. For example, 'पाइथन क्या है?' becomes "
                    "'Python kya hai?'. Do not answer the question, translate "
                    "it into English, or add explanations. Return only the "
                    "transliterated question."
                ),
            },
            {"role": "user", "content": transcript},
        ],
        temperature=0,
    )

    return (chat_result.choices[0].message.content or "").strip()

