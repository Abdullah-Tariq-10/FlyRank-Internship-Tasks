from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from openai import OpenAI
from pydantic import ValidationError

from src.llm.schema import TriageResponse

PROMPT_VERSION = "triage-v1"
PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"
LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "logs"



def load_system_prompt(version: str = PROMPT_VERSION) -> str:
    prompt_file = PROMPTS_DIR / f"{version}.md"
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt spec file not found: {prompt_file}")
    with open(prompt_file, "r", encoding="utf-8") as f:
        return f.read().strip()


def get_llm_client() -> OpenAI:
    return OpenAI(
        base_url=os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1/"),
        api_key=os.environ.get("LLM_API_KEY", "ollama"),
    )


def extract_json_string(raw_text: str) -> str:
    """
    Step 1: Strips markdown backticks (```json ... ```) 
    and uses regex to extract only the outermost JSON structure { ... }.
    """
    cleaned = raw_text.strip()
    # Strip markdown fence indicators
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned).strip()

    # Match the outermost JSON object bounds
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        return match.group(0).strip()
    return cleaned



def quarantine_failure(user_text: str, raw_output: str, error_msg: str, prompt_version: str = PROMPT_VERSION):
    """
    Step 4: Appends unrecoverable schema validation failures to logs/quarantine.jsonl.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    quarantine_file = LOGS_DIR / "quarantine.jsonl"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": prompt_version,
        "input_text": user_text,
        "raw_output": raw_output,
        "error": error_msg,
    }
    with open(quarantine_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")



def execute_triage(user_text: str) -> TriageResponse:
    """
    Coordinates the full pipeline:
    1. First Call
    2. Parsing & Pydantic Validation
    3. Exactly One Repair Call on failure
    4. Quarantine Logging & 422 trigger on secondary failure
    """
    client = get_llm_client()
    system_prompt = load_system_prompt(PROMPT_VERSION)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text},
    ]

    # --- ATTEMPT 1: Initial LLM Execution ---
    response = client.chat.completions.create(
        model=os.environ.get("LLM_MODEL", "gemma3:1b"),
        messages=messages,
        temperature=0.0,
    )
    raw_output = response.choices[0].message.content.strip()

    try:
        # Step 1 & 2: Parse string and validate against Pydantic schema
        json_str = extract_json_string(raw_output)
        return TriageResponse.model_validate_json(json_str)
    except (ValidationError, ValueError, json.JSONDecodeError) as err_1:
        first_error_msg = str(err_1)

        # --- ATTEMPT 2: The Repair Retry (Step 3) ---
        # Feed the model its own broken output + the specific validator rejection message
        repair_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": raw_output},
            {
                "role": "user",
                "content": (
                    f"Your previous output was rejected by the schema validator for this error:\n"
                    f"{first_error_msg}\n\n"
                    f"Return ONLY a single corrected JSON object matching the required schema."
                ),
            },
        ]

        repair_response = client.chat.completions.create(
            model=os.environ.get("LLM_MODEL", "gemma3:1b"),
            messages=repair_messages,
            temperature=0.0,
        )
        repair_raw = repair_response.choices[0].message.content.strip()

        try:
            repair_json_str = extract_json_string(repair_raw)
            return TriageResponse.model_validate_json(repair_json_str)
        except (ValidationError, ValueError, json.JSONDecodeError) as err_2:
            # Step 4: Secondary failure -> Quarantine and raise ValueError
            final_error_msg = f"Repair failed. Attempt 1: {first_error_msg} | Attempt 2: {str(err_2)}"
            quarantine_failure(user_text, repair_raw, final_error_msg, PROMPT_VERSION)
            raise ValueError(final_error_msg)








