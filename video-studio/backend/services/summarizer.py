import os
from openai import OpenAI

def generate_summary(text: str) -> str:
    """
    Summarizes business news into 3-4 bullet points in simple language.
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    prompt = f"Summarize this business news into 3-4 bullet points in simple language:\n\n{text}"
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes news."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=300
    )
    
    return response.choices[0].message.content.strip()
