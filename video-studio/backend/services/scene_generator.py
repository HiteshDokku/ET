import os
import json
from openai import OpenAI

def generate_scenes(script: str) -> list[dict]:
    """
    Breaks a script into 4-6 scenes.
    Returns JSON array: [{"text": "...", "type": "text" | "data"}]
    """
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("XAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1"
    )
    prompt = (
        f"Break this script into 4-6 scenes. "
        f"For each scene return a JSON object with 'text' (the narration) and 'type' ('text' or 'data'). "
        f"If data/statistics/numbers are prominent, mark type as 'data'. Otherwise 'text'.\n\n"
        f"Respond ONLY with a valid JSON array of objects. Do not include markdown formatting.\n\n"
        f"Script:\n{script}"
    )
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a JSON generator that outputs strictly JSON without backticks or markdown."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=800
    )
    
    content = response.choices[0].message.content.strip()
    
    # Simple cleanup just in case there are markdown blocks
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
        
    content = content.strip()
    
    try:
        scenes = json.loads(content)
        return scenes
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        # Fallback scenes
        return [
            {"text": script, "type": "text"}
        ]
