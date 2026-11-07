
import json
import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv(
    "GROQ_CHAT_MODEL",
    "openai/gpt-oss-20b",
)

client = Groq(api_key=API_KEY) if API_KEY else None


def generate_summary(transcript_text: str) -> dict:
    if client is None:
        raise RuntimeError("GROQ_API_KEY is missing from .env")

    if not transcript_text or not transcript_text.strip():
        raise ValueError("Transcript cannot be empty.")

    prompt = """
You are a professional meeting summarization assistant.

Summarize the supplied meeting transcript using only information
contained in the transcript.

Return a valid JSON object with exactly these keys:
{
  "overview": "A concise meeting overview in 2-3 sentences.",
  "key_points": ["..."],
  "important_decisions": ["..."],
  "action_items": [
    {
      "task": "...",
      "owner": "Person's name or Not specified",
      "deadline": "Mentioned deadline or Not specified"
    }
  ]
}

Rules:
1. Overview: exactly 2 or 3 sentences.
2. Key points: maximum 5 items.
3. Important decisions: maximum 5 items.
4. Action items: include concrete tasks or commitments only.
5. Do not invent decisions, owners, or deadlines.
6. Use empty arrays when no items are supported by the transcript.
7. Return JSON only, without Markdown fences.
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": (
                    "Summarize this meeting transcript:\n\n"
                    + transcript_text
                    + "\n\nReturn a valid JSON object containing "
                    "overview, key_points, important_decisions, "
                    "and action_items."
                ),
            },
        ],
        response_format={"type": "json_object"},
        max_completion_tokens=3000,
        temperature=0.2,
    )

    content = response.choices[0].message.content

    if not content:
        raise RuntimeError("The model returned an empty summary.")

    summary = json.loads(content)

    if not isinstance(summary, dict):
        raise ValueError("The model did not return a JSON object.")

    summary["key_points"] = summary.get("key_points", [])[:5]
    summary["important_decisions"] = (
        summary.get("important_decisions", [])[:5]
    )
    summary["action_items"] = summary.get("action_items", [])

    return summary
