import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_briefing(articles):

    articles_text = ""

    for i, article in enumerate(articles):
        articles_text += f"""
Article {i+1}
Title: {article['title']}
Content: {article['content']}
"""

    prompt = f"""
You are an Economic Times financial analyst.

Below are multiple articles about the SAME topic.

{articles_text}

Create a deep intelligence briefing.

Write it in detail and easy language for user to understand.

Return ONLY valid JSON with the following exact structure:

{{
  "briefing": {{
    "Summary": "A concise overview",
    "Key Insights": ["Insight 1", "Insight 2"],
    "Market Impact": "Description of market impact",
    "What To Watch": "Future outlook",
    "Controversies / Concerns": "Controversies / Concerns",
  }},
  "followups": ["Question 1", "Question 2", "Question 3"]
}}

Synthesize across all articles.
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=3500
    )

    output = response.choices[0].message.content

    # Remove ```json formatting if present
    output = re.sub(r"```json", "", output)
    output = re.sub(r"```", "", output).strip()

    try:
        parsed = json.loads(output)

        return {
            "briefing": parsed["briefing"],
            "followups": parsed.get("followups", [])
        }

    except Exception as e:
        print("Parsing error:", e)
        print("Raw output:", output)

        return {
            "briefing": output,
            "followups": []
        }