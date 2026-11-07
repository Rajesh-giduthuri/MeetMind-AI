
import os
import sys

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
transcription_model = os.getenv(
    "GROQ_TRANSCRIPTION_MODEL",
    "whisper-large-v3",
)
chat_model = os.getenv(
    "GROQ_CHAT_MODEL",
    "openai/gpt-oss-20b",
)

if not api_key or api_key == "your_actual_groq_api_key_here":
    sys.exit("ERROR: Add your actual Groq API key to .env")

try:
    client = Groq(api_key=api_key)

    print("\nChecking Groq API connection...")

    models = client.models.list()
    available_models = {model.id for model in models.data}

    print("API connection successful!")

    print("\nChecking selected models:")

    for model_name in [transcription_model, chat_model]:
        if model_name in available_models:
            print(f"FOUND: {model_name}")
        else:
            print(f"NOT LISTED: {model_name}")

    print("\nTesting chat model...")

    response = client.chat.completions.create(
        model=chat_model,
        messages=[
            {
                "role": "user",
                "content": "Reply with exactly: Groq connection successful",
            }
        ],
        max_completion_tokens=100,
    )

    print("Chat model response:")
    print(response.choices[0].message.content)

    print("\nGroq chat test completed!")

except Exception as error:
    print("\nGroq API test failed.")
    print(f"Error type: {type(error).__name__}")
    print(f"Details: {error}")
