import os
from pathlib import Path
from openai import OpenAI

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"

def load_system_prompt(version: str = "triage-v1") -> str:
    """Reads the prompt markdwon sepcificaition from the versioned file."""
    prompt_file = PROMPTS_DIR / f"{version}.md"
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt spec file not found: {prompt_file}")
    with open(prompt_file, "r", encoding="utf-8") as f:
        return f.read().strip()

def get_llm_client() -> OpenAI:
    """Initializes the provider-agnostic OpenAI client."""
    return OpenAI(
        base_url=os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1/"),
        api_key=os.environ.get("LLM_API_KEY", "ollama"),
    )

def call_llm(user_text: str, prompt_version: str = "triage-v1") -> str:
    """Sends the system prompt and separated user payload with zero temperature."""
    client = get_llm_client()
    system_prompt = load_system_prompt(prompt_version)

    response = client.chat.completions.create(
        model=os.environ.get("LLM_MODEL", "gemma3:1b"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},  # Kept in user role for prompt injection safety
        ],
        temperature=0.0,  # Low temperature ensures deterministic outputs
    )
    return response.choices[0].message.content.strip()