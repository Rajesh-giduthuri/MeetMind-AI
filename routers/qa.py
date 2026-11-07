
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from database import SessionLocal
from models import Meeting, MeetingQuestion
from qa_service import answer_meeting_question

router = APIRouter(prefix="/api/meetings", tags=["Q&A"])


class QuestionRequest(BaseModel):
    question: str


@router.post("/{meeting_id}/ask")
def ask_meeting_question(
    meeting_id: str,
    request: QuestionRequest,
    session_request: Request,
):
    user_id = session_request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Please log in to ask questions.",
        )

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
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

        if not meeting.transcript_text:
            raise HTTPException(
                status_code=400,
                detail="This meeting has no transcript.",
            )

        is_document = meeting.filename.lower().endswith(
            (".pdf", ".docx")
        )

        if is_document:
            if not meeting.summary:
                raise HTTPException(
                    status_code=400,
                    detail="This document has no summary.",
                )

            answer = answer_meeting_question(
                transcript="",
                summary=meeting.summary,
                question=question,
            )
        else:
            if not meeting.transcript_text:
                raise HTTPException(
                    status_code=400,
                    detail="This meeting has no transcript.",
                )

            answer = answer_meeting_question(
                transcript=meeting.transcript_text,
                summary=meeting.summary or {},
                question=question,
            )

        saved_question = MeetingQuestion(
            meeting_id=meeting.id,
            question=question,
            answer=answer,
        )

        db.add(saved_question)
        db.commit()
        db.refresh(saved_question)

        return {
            "meeting_id": meeting.id,
            "question": question,
            "answer": answer,
            "created_at": (
                saved_question.created_at.isoformat()
                if saved_question.created_at else None
            ),
        }

    except HTTPException:
        raise

    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Question answering failed: {error}",
        ) from error

    finally:
        db.close()


@router.get("/{meeting_id}/questions")
def get_meeting_questions(meeting_id: str, request: Request):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Please log in to view question history.",
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

        questions = db.query(MeetingQuestion).filter(
            MeetingQuestion.meeting_id == meeting_id
        ).all()

        return {
            "meeting_id": meeting_id,
            "questions": [
                {
                    "id": question.id,
                    "question": question.question,
                    "answer": question.answer,
                    "created_at": (
                        question.created_at.isoformat()
                        if question.created_at else None
                    ),
                }
                for question in questions
            ],
        }

    finally:
        db.close()
