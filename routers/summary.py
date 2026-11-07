
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from summary_service import generate_summary

router = APIRouter(prefix="/api/meetings", tags=["Summary"])


class SummaryRequest(BaseModel):
    transcript_text: str


@router.post("/summary")
def summarize_meeting(request: SummaryRequest):
    try:
        summary = generate_summary(request.transcript_text)
        return {"summary": summary}

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Summary generation failed: {error}",
        ) from error
