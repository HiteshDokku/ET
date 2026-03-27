from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json

from gemma_api import generate_briefing, client
from scraper import scrape_topic

app = FastAPI()

# Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store last briefing for follow-up questions
last_briefing = ""


# -------------------------------
# Models
# -------------------------------

class AskRequest(BaseModel):
    question: str


class GenerateRequest(BaseModel):
    topic: str


# -------------------------------
# Routes
# -------------------------------

@app.get("/")
def home():
    return {"status": "running"}


@app.post("/generate")
def generate(req: GenerateRequest):
    global last_briefing

    topic = req.topic

    # Scrape Economic Times dynamically
    articles = scrape_topic(topic)

    # Fallback if scraping fails
    if not articles:
        return {
            "briefing": {
                "Summary": "No articles found for this topic.",
                "Key Insights": ["Try another topic"],
                "Market Impact": "N/A",
                "Controversies": "N/A",
                "What To Watch": "N/A"
            },
            "followups": [],
            "articles": []   # added
        }

    # Generate briefing
    result = generate_briefing(articles)

    # Convert briefing to readable text
    if isinstance(result["briefing"], dict):
        last_briefing = json.dumps(result["briefing"], indent=2)
    else:
        last_briefing = result["briefing"]

    # return articles also
    return {
        "briefing": result["briefing"],
        "followups": result["followups"],
        "articles": articles
    }


@app.post("/ask")
def ask_question(req: AskRequest):
    global last_briefing

    prompt = f"""
You are an Economic Times financial analyst.

Here is the information from the analyzed articles:

{last_briefing}

User question:
{req.question}

Answer clearly and concisely based only on the provided information. 
When referring to the source of your information, use phrases like "According to the articles" instead of "According to the briefing".
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=800
    )

    answer = response.choices[0].message.content

    return {"answer": answer}