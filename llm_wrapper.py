import os
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "mistral-saba-24b"  # ✅ your correct model

def call_grok_api(prompt):
    if not GROQ_API_KEY:
        raise ValueError("❌ GROQ_API_KEY not found. Please check your .env file.")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that writes clean Python docstrings for developers."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=data)
    print(f"🔁 Status: {response.status_code}")
    print(f"📨 Response text: {response.text[:300]}...")

    response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"]
