import re

def clean_article_text(text: str) -> str:
    """Removes extra spaces and line breaks from the raw article input."""
    if not text:
        return ""
    # Replace multiple newlines or spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
