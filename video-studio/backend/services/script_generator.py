from utils.llm_client import get_llm_client_and_model

def generate_script(summary: str) -> str:
    """
    Converts a summary into a 60-second news anchor script with short, engaging sentences.
    """
    client, model_name = get_llm_client_and_model()
    prompt = (
        f"Convert this bullet point summary into a 60-second news anchor script. "
        f"Keep sentences short, punchy, and engaging for a fast-paced video.\n\nSummary:\n{summary}"
    )
    
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are an expert news scriptwriter."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=500
    )
    
    return response.choices[0].message.content.strip()
