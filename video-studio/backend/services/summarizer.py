from utils.llm_client import get_llm_client_and_model

def generate_summary(text: str) -> str:
    """
    Summarizes business news into 3-4 bullet points in simple language.
    """
    client, model_name = get_llm_client_and_model()
    prompt = f"Summarize this business news into 3-4 bullet points in simple language:\n\n{text}"
    
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes news."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=300
    )
    
    return response.choices[0].message.content.strip()
