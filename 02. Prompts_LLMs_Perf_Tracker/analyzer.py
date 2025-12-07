# llm_tracker/analyzer.py

import re

def analyze_response(response_text, brand_keywords):
    """Basic analysis: brand presence, sentiment, and optional rank estimation."""
    lower_text = response_text.lower()

    # Brand mention check
    brand_mentioned = any(brand.lower() in lower_text for brand in brand_keywords)

    # Sentiment check (rule-based fallback — replace with LLM classification if needed)
    if "best" in lower_text or "recommended" in lower_text or "top" in lower_text:
        sentiment = "positive"
    elif "avoid" in lower_text or "not recommended" in lower_text or "problem" in lower_text:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    # Rank estimation (looks for your brand in a list like 1. Foo, 2. Bar)
    rank = extract_rank(response_text, brand_keywords)

    return {
        "brand_mentioned": brand_mentioned,
        "sentiment": sentiment,
        "rank": rank,
    }

def extract_rank(text, brand_keywords):
    """If there's a numbered list, check for brand position."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if any(brand.lower() in line.lower() for brand in brand_keywords):
            if re.match(r"^\s*\d+[.)]", line):
                return i + 1
    return None
