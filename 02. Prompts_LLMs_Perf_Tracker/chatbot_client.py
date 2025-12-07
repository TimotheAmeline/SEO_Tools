import os
import requests
from dotenv import load_dotenv
from openai import OpenAI
import anthropic

# Load .env vars
load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Gemini endpoint
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"

def query_chatbot(platform, prompt):
    if platform == "OpenAI":
        return query_openai(prompt)
    elif platform == "Gemini":
        return query_gemini(prompt)
    elif platform == "Claude":
        return query_claude(prompt)
    elif platform == "Perplexity":
        return "⚠️ Perplexity integration not available – no public API yet."
    elif platform == "Grok":
        return "⚠️ Grok integration not available – requires X Premium API access."
    else:
        raise ValueError(f"Unknown platform: {platform}")

def query_openai(prompt):
    if not OPENAI_API_KEY:
        raise EnvironmentError("❌ OPENAI_API_KEY is missing. Set it in your environment variables or .env file.")

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=1000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise RuntimeError(f"❌ OpenAI query failed: {e}")

def query_gemini(prompt):
    if not GEMINI_API_KEY:
        raise EnvironmentError("❌ GEMINI_API_KEY is missing. Set it in your environment variables or .env file.")

    try:
        headers = {"Content-Type": "application/json"}
        body = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        full_url = f"{GEMINI_URL}?key={GEMINI_API_KEY}"
        res = requests.post(full_url, headers=headers, json=body)
        res.raise_for_status()
        candidates = res.json().get("candidates", [])
        if candidates:
            return candidates[0]["content"]["parts"][0]["text"].strip()
        return ""
    except Exception as e:
        raise RuntimeError(f"❌ Gemini query failed: {e}")

def query_claude(prompt):
    if not ANTHROPIC_API_KEY:
        raise EnvironmentError("❌ ANTHROPIC_API_KEY is missing. Set it in your environment variables or .env file.")

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1000,
            temperature=0.5,
            system="You are a helpful assistant.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text.strip()
    except Exception as e:
        raise RuntimeError(f"❌ Claude query failed: {e}")
