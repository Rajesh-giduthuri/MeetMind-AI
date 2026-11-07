
import os
import json

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "openai/gpt-oss-20b"



def answer_meeting_question(
    transcript: str,
    summary: dict,
    question: str,
) -> str:
    is_document = not transcript.strip()

    if is_document:
        context = (
            "DOCUMENT SUMMARY:\n"
            + json.dumps(summary, ensure_ascii=False, indent=2)
        )
        missing_message = (
            "This was not mentioned in the document summary."
        )
        source_name = "document summary"
    else:
        context = (
            f"MEETING TRANSCRIPT:\n{transcript}\n\n"
            f"MEETING SUMMARY:\n"
            f"{json.dumps(summary, ensure_ascii=False, indent=2)}"
        )
        missing_message = (
            "This was not mentioned in this meeting."
        )
        source_name = "provided meeting transcript and summary"


    system_prompt = f"""
You are MeetMind AI, an intelligent meeting assistant.

STRICT RULES:

1. Use ONLY the provided meeting transcript and summary.
   For documents, use ONLY the provided document summary.
2. Never invent facts or use information from other meetings.
3. If information is missing, reply:
   "{missing_message}"

LANGUAGE AND FORMAT RULES:

4. Detect the language and script of the user's question.
5. If the question uses Hinglish written in English letters,
   answer in Roman-script Hinglish using English letters only.
6. Never use Devanagari script when the question is in
   Roman-script Hinglish.
7. If the question is in English, answer entirely in English.
8. If the question is in Hindi written in Devanagari,
   answer in Hindi using Devanagari script.
9. For Roman-script Hinglish, use natural conversational wording.
   Example question: "Kya is meeting mein decisions liye gaye?"
   Example answer: "Haan, meeting mein kai decisions liye gaye."
10. For English questions, do not include Hindi or Hinglish words.
11. Keep the same language and script throughout the answer.
12. Apply these rules consistently for every user account.

ANSWER QUALITY RULES:

11. Answer the exact question directly and completely.
12. For questions asking "who", include the person's name
    and the relevant explanation supported by the context.
13. Prefer complete sentences instead of short, incomplete answers.
14. Preserve names, dates, decisions, and action items accurately.
15. Use plain text. Do not use Markdown formatting,
    asterisks, headings, or unnecessary numbered lists.
16. Keep answers concise but informative.

HINGLISH EXAMPLE:

Question: kisko counseling arrange karna hai

Answer: John Smith ko counseling arrange karna hai,
kyunki usne apne parents ki madad karne aur chhote
siblings ki dekhbhaal ke karan bahut stress feel kiya hai.

Follow the language and script rules for every user.
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": (
                    f"{context}\n\n"
                    f"QUESTION:\n{question}"
                ),
            },
        ],
        temperature=0.2,
        max_completion_tokens=700,
    )

    answer = response.choices[0].message.content or ""
    answer = answer.strip()

    # Remove common Markdown formatting if the model returns it.
    answer = answer.replace("**", "").replace("__", "")
    answer = answer.replace("```", "").replace("`", "")

    return answer or missing_message
