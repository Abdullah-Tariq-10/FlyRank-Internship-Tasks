from datetime import datetime, timezone
import json
import random
import time
import hashlib
from typing import Any, Dict, Tuple
from openai import APIConnectionError, APIStatusError, APITimeoutError
import os
from pathlib import Path
import re
from openai import OpenAI
from pydantic import ValidationError

from src.llm.schema import TriageResponse

#PROMPT_VERSION = "triage-v1"
PROMPT_VERSION = "triage-v2"
PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"
LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# In-memory Response Cache
RESPONSE_CACHE: dict[str, TriageResponse] = {}


def get_cache_key(prompt_version: str, user_text: str) -> str:
    """Computes a deterministic cache key combining prompt version and normalized text."""
    normalized_input = f"{prompt_version}:{user_text.strip().lower()}"
    return hashlib.sha256(normalized_input.encode("utf-8")).hexdigest()


def load_system_prompt(version: str = PROMPT_VERSION) -> str:
    prompt_file = PROMPTS_DIR / f"{version}.md"
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt spec file not found: {prompt_file}")
    with open(prompt_file, "r", encoding="utf-8") as f:
        return f.read().strip()


def get_llm_client() -> OpenAI:
    """Initializes client with an explicit 30s timeout and disables silent SDK retries."""
    return OpenAI(
        base_url=os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1/"),
        api_key=os.environ.get("LLM_API_KEY", "ollama"),
        timeout=30.0,
        max_retries=0,
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
    Coordinates the full Stage 4 production pipeline:
    1. In-memory caching lookup (Extra)
    2. Model call with custom backoff/jitter retry policy
    3. Parsing & Pydantic schema validation
    4. Exactly one repair call on validation failure
    5. Cache write, structured usage logging, and quarantine on unrecoverable failure
    """
    system_prompt = load_system_prompt(PROMPT_VERSION)
    model_name = os.environ.get("LLM_MODEL", "gemma3:1b")

    # 1. Check In-Memory Cache
    cache_key = get_cache_key(PROMPT_VERSION, user_text)
    if cache_key in RESPONSE_CACHE:
        # Cache hit: instant return, 0 tokens, 0ms duration
        log_cost_metric(
            PROMPT_VERSION,
            f"{model_name}-cached",
            input_tokens=0,
            output_tokens=0,
            duration_ms=0.0,
            needed_repair=False,
        )
        return RESPONSE_CACHE[cache_key]

    print(f"[CACHE MISS] Calling LLM ({model_name})...")
    client = get_llm_client()
    start_time = time.time()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text},
    ]

    needed_repair = False
    raw_output, usage = call_with_retry(client, model_name, messages)

    try:
        json_str = extract_json_string(raw_output)
        result = TriageResponse.model_validate_json(json_str)
        
        # Save valid result into cache
        RESPONSE_CACHE[cache_key] = result
        
        # Log successful initial call
        log_cost_metric(
            PROMPT_VERSION,
            model_name,
            usage["prompt_tokens"],
            usage["completion_tokens"],
            (time.time() - start_time) * 1000,
            needed_repair=False,
        )
        return result
    except (ValidationError, ValueError, json.JSONDecodeError) as err_1:
        needed_repair = True
        first_error_msg = str(err_1)

        # Attempt 2: Repair Retry
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

        repair_raw, repair_usage = call_with_retry(client, model_name, repair_messages)
        total_in_tokens = usage["prompt_tokens"] + repair_usage["prompt_tokens"]
        total_out_tokens = usage["completion_tokens"] + repair_usage["completion_tokens"]

        try:
            repair_json_str = extract_json_string(repair_raw)
            result = TriageResponse.model_validate_json(repair_json_str)
            
            # Save repaired result into cache
            RESPONSE_CACHE[cache_key] = result
            
            # Log successful repair call
            log_cost_metric(
                PROMPT_VERSION,
                model_name,
                total_in_tokens,
                total_out_tokens,
                (time.time() - start_time) * 1000,
                needed_repair=True,
            )
            return result
        except (ValidationError, ValueError, json.JSONDecodeError) as err_2:
            final_error_msg = f"Repair failed. Attempt 1: {first_error_msg} | Attempt 2: {str(err_2)}"
            quarantine_failure(user_text, repair_raw, final_error_msg, PROMPT_VERSION)
            # Log failed run to usage before raising
            log_cost_metric(
                PROMPT_VERSION,
                model_name,
                total_in_tokens,
                total_out_tokens,
                (time.time() - start_time) * 1000,
                needed_repair=True,
            )
            raise ValueError(final_error_msg)


def call_with_retry(client: OpenAI, model: str, messages: list, max_retries: int = 2) -> Tuple[str, Dict[str, Any]]:
    """
    Executes chat completion with exponential backoff and jitter.
    Retries only on transient network timeouts, 429, and 5xx errors.
    Never retries 400, 401, or 403.
    """
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.0,
            )
            raw_text = response.choices[0].message.content.strip()
            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            }
            return raw_text, usage

        except (APITimeoutError, APIConnectionError) as net_err:
            if attempt == max_retries:
                raise TimeoutError(f"LLM request timed out after {max_retries + 1} attempts: {str(net_err)}")
            delay = (2 ** attempt) + random.uniform(0.1, 0.5)
            time.sleep(delay)

        except APIStatusError as status_err:
            # 400, 401, 403 are terminal configuration errors — never retry
            if status_err.status_code in (400, 401, 403):
                raise PermissionError(f"LLM client authorization error ({status_err.status_code}): {status_err.message}")

            # 429 and 5xx are transient rate/server errors — retry with backoff
            if status_err.status_code == 429 or status_err.status_code >= 500:
                if attempt == max_retries:
                    raise RuntimeError(f"LLM upstream error ({status_err.status_code}) after retries: {status_err.message}")

                retry_after = status_err.response.headers.get("Retry-After") if hasattr(status_err, "response") else None
                if retry_after and retry_after.isdigit():
                    delay = float(retry_after)
                else:
                    delay = (2 ** attempt) + random.uniform(0.1, 0.5)
                time.sleep(delay)
            else:
                raise status_err



def log_cost_metric(
    prompt_version: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    duration_ms: float,
    needed_repair: bool,
):
    """Writes a single structured JSON line per LLM call to logs/usage.jsonl."""
    usage_file = LOGS_DIR / "usage.jsonl"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": prompt_version,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "duration_ms": round(duration_ms, 2),
        "needed_repair": needed_repair,
    }
    with open(usage_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
