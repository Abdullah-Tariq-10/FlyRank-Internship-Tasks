import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url=os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1/"),
    api_key=os.environ.get("LLM_API_KEY", "ollama"),
)

response = client.chat.completions.create(
    model=os.environ.get("LLM_MODEL", "gemma3:1b"),
    messages=[
        {"role": "user", "content": "Reply with exactly the word: ready"}
    ],
    temperature=0.0,
)

print("Model output:", response.choices[0].message.content.strip())