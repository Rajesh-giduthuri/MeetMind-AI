from pathlib import Path
from pypdf import PdfReader
from docx import Document


def extract_document_text(file_path: str) -> str:
    path = Path(file_path)
    extension = path.suffix.lower()

    if extension == ".pdf":
        reader = PdfReader(str(path))
        text = "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )

    elif extension == ".docx":
        document = Document(str(path))
        text = "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        )

    else:
        raise ValueError("Only PDF and DOCX files are supported.")

    if not text.strip():
        raise ValueError(
            "No readable text found. The document may be scanned "
            "or contain images instead of selectable text."
        )

    return text.strip()