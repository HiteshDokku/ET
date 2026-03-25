import os
from openai import OpenAI

def get_llm_client_and_model():
    """
    Returns a configured OpenAI-compatible client and the appropriate model name
    based on the available environment variables.
    Priority: 1. GROQ_API_KEY 2. XAI_API_KEY (Grok) 3. OPENAI_API_KEY
    """
    if os.getenv("GROQ_API_KEY"):
        client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1"
        )
        return client, "llama-3.3-70b-versatile"
        
    elif os.getenv("XAI_API_KEY"):
        client = OpenAI(
            api_key=os.getenv("XAI_API_KEY"),
            base_url="https://api.x.ai/v1"
        )
        return client, "grok-2"
        
    elif os.getenv("OPENAI_API_KEY"):
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        return client, "gpt-4o"
        
    else:
        raise ValueError("No valid API Key found! Please set GROQ_API_KEY, XAI_API_KEY, or OPENAI_API_KEY")
