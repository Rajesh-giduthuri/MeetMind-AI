
import json
from datetime import datetime
from io import BytesIO

from docx import Document
from docx.shared import Inches
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    ListFlowable,
    ListItem,
)
def format_created_at(value):
    if not value:
        return "Not available"

    return value.strftime("%d-%m-%Y, %H:%M:%S")

def _format_value(value):
    """Convert summary values into readable text."""
    if value is None:
        return "Not specified"

    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)

    return str(value)


def _format_timestamp(value):
    """Format a timestamp when available."""
    if value is None:
        return "Timestamp not available"

    if isinstance(value, (int, float)):
        seconds = max(0, int(value))
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    return str(value)


def _get_segments(meeting):
    """Return transcript segments if available."""
    segments = meeting.transcript_segments or []

    if isinstance(segments, str):
        try:
            segments = json.loads(segments)
        except (json.JSONDecodeError, TypeError):
            return []

    return segments if isinstance(segments, list) else []


def _get_summary(meeting):
    summary = meeting.summary or {}

    if isinstance(summary, str):
        try:
            summary = json.loads(summary)
        except (json.JSONDecodeError, TypeError):
            return {}

    return summary if isinstance(summary, dict) else {}


def _add_summary_sections(add_heading, add_text, add_list, meeting):
    summary = _get_summary(meeting)

    add_heading("Meeting Overview")
    add_text(
        _format_value(summary.get("overview", "Not available"))
    )

    add_heading("Key Points")
    add_list(summary.get("key_points", []))

    add_heading("Important Decisions")
    add_list(summary.get("important_decisions", []))

    add_heading("Action Items")
    action_items = summary.get("action_items", [])

    if not isinstance(action_items, list) or not action_items:
        add_text("No action items available.")
    else:
        for index, item in enumerate(action_items, start=1):
            if isinstance(item, dict):
                task = item.get("task", "Not specified")
                owner = item.get("owner", "Not specified")
                deadline = item.get("deadline", "Not specified")

                add_text(
                    f"{index}. {task} | Owner: {owner} "
                    f"| Deadline: {deadline}"
                )
            else:
                add_text(f"{index}. {_format_value(item)}")


def generate_pdf_report(meeting):
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
    )

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            alignment=TA_CENTER,
            textColor=colors.HexColor("#243B53"),
            spaceAfter=16,
        )
    )

    story = []

    def add_heading(text):
        story.append(Paragraph(text, styles["Heading2"]))
        story.append(Spacer(1, 5))

    def add_text(text):
        safe_text = (
            _format_value(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br/>")
        )
        story.append(Paragraph(safe_text, styles["BodyText"]))
        story.append(Spacer(1, 7))

    def add_list(items):
        if not isinstance(items, list) or not items:
            add_text("None recorded.")
            return

        list_items = []
        for item in items:
            safe_item = (
                _format_value(item)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br/>")
            )
            list_items.append(
                ListItem(
                    Paragraph(safe_item, styles["BodyText"]),
                    leftIndent=12,
                )
            )

        story.append(ListFlowable(list_items, bulletType="bullet"))
        story.append(Spacer(1, 8))

    title = meeting.filename or "Meeting Report"
    story.append(Paragraph("MeetMind AI", styles["ReportTitle"]))
    story.append(Paragraph("Meeting Report", styles["Heading1"]))
    story.append(Spacer(1, 8))

    add_heading("Meeting Details")
    add_text(f"Title: {title}")
    add_text(f"Meeting ID: {meeting.id}")
    add_text(
        "Created: "
        + (
            format_created_at(meeting.created_at)
        )
    )
    add_text(f"Status: {meeting.status or 'Not specified'}")

    _add_summary_sections(
        add_heading, add_text, add_list, meeting
    )

    # add_heading("Transcript")

    # segments = _get_segments(meeting)

    # if segments:
    #     for segment in segments:
    #         if not isinstance(segment, dict):
    #             continue

    #         timestamp = _format_timestamp(
    #             segment.get("start", segment.get("timestamp"))
    #         )
    #         text = segment.get(
    #             "text",
    #             segment.get("transcript", ""),
    #         )

    #         if text:
    #             add_text(f"[{timestamp}] {text}")
    # else:
    #     add_text(
    #         meeting.transcript_text or "Transcript not available."
    #     )

    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_docx_report(meeting):
    doc = Document()

    doc.add_heading("MeetMind AI — Meeting Report", level=0)
    doc.add_heading("Meeting Details", level=1)

    doc.add_paragraph(f"Title: {meeting.filename or 'Meeting Report'}")
    doc.add_paragraph(f"Meeting ID: {meeting.id}")
    doc.add_paragraph(
        "Created: "
        + (
            format_created_at(meeting.created_at)
        )
    )
    doc.add_paragraph(f"Status: {meeting.status or 'Not specified'}")

    def add_heading(text):
        doc.add_heading(text, level=1)

    def add_text(text):
        doc.add_paragraph(_format_value(text))

    def add_list(items):
        if not isinstance(items, list) or not items:
            doc.add_paragraph("None recorded.")
            return

        for item in items:
            doc.add_paragraph(
                _format_value(item),
                style="List Bullet",
            )

    _add_summary_sections(
        add_heading, add_text, add_list, meeting
    )

    # doc.add_heading("Transcript", level=1)

    # segments = _get_segments(meeting)

    # if segments:
    #     for segment in segments:
    #         if not isinstance(segment, dict):
    #             continue

    #         timestamp = _format_timestamp(
    #             segment.get("start", segment.get("timestamp"))
    #         )
    #         text = segment.get(
    #             "text",
    #             segment.get("transcript", ""),
    #         )

    #         if text:
    #             doc.add_paragraph(f"[{timestamp}] {text}")
    # else:
    #     doc.add_paragraph(
    #         meeting.transcript_text or "Transcript not available."
    #     )

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer
