# llm_wrapper.py
import os
import time
import json
from typing import Optional, Dict, Any, List

import requests
from dotenv import load_dotenv

load_dotenv()

# -------- Config (env-overridable) --------
GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_API_URL: str = f"{GROQ_BASE_URL.rstrip('/')}/chat/completions"

# Primary default (per Groq deprecation notice, 2025-07-30)
DEFAULT_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3-32b")

# Ordered fallbacks you’re happy to use if the default is deprecated/unavailable
AUTO_FAILOVER_MODELS: List[str] = [
    DEFAULT_MODEL,
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]

DEFAULT_TIMEOUT_SECS = int(os.getenv("GROQ_TIMEOUT_SECS", "60"))
DEFAULT_RETRIES = int(os.getenv("GROQ_RETRIES", "2"))
DEFAULT_BACKOFF = float(os.getenv("GROQ_BACKOFF", "1.5"))  # exponential base


class LLMHTTPError(RuntimeError):
    pass


def _headers() -> Dict[str, str]:
    if not GROQ_API_KEY:
        raise ValueError("❌ GROQ_API_KEY not found. Set it in your environment or .env file.")
    return {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}


def _extract_text_or_error(resp: requests.Response) -> str:
    try:
        data = resp.json()
    except json.JSONDecodeError:
        raise LLMHTTPError(f"Non-JSON response (status {resp.status_code}): {resp.text[:300]}")

    # Normal success shape
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        # Error shape from Groq
        err = data.get("error") or {}
        msg = err.get("message", "")
        code = err.get("code", "")
        raise LLMHTTPError(f"API error (status {resp.status_code}) code={code}: {msg}")


def _request_once(payload: Dict[str, Any], timeout: int) -> str:
    resp = requests.post(GROQ_API_URL, headers=_headers(), json=payload, timeout=timeout)
    if 200 <= resp.status_code < 300:
        return _extract_text_or_error(resp)

    req_id = resp.headers.get("x-request-id") or resp.headers.get("x-requestid")
    body = resp.text[:300]
    raise LLMHTTPError(
        f"HTTP {resp.status_code} from Groq."
        + (f" request_id={req_id}." if req_id else "")
        + f" body: {body}"
    )


def _should_retry(err_msg: str) -> bool:
    return any(x in err_msg for x in ["HTTP 429", "HTTP 500", "HTTP 502", "HTTP 503", "HTTP 504"])


def _is_decommissioned(err_msg: str) -> bool:
    return "decommissioned" in err_msg.lower() or "model_decommissioned" in err_msg.lower()


def call_grok_api(
    prompt: str,
    *,
    system_prompt: Optional[str] = "You are a helpful assistant that writes clean Python docstrings for developers.",
    temperature: float = 0.2,
    max_tokens: Optional[int] = None,
    timeout: int = DEFAULT_TIMEOUT_SECS,
    retries: int = DEFAULT_RETRIES,
    backoff_base: float = DEFAULT_BACKOFF,
    model: Optional[str] = None,
) -> str:
    """
    Robust call to Groq's OpenAI-compatible /chat/completions endpoint with automatic
    fallback if the selected model is decommissioned.
    """
    if not prompt or not isinstance(prompt, str):
        raise ValueError("prompt must be a non-empty string.")

    # Build list of models to try (override goes first if provided)
    models_to_try: List[str] = []
    if model:
        models_to_try.append(model)
    for m in AUTO_FAILOVER_MODELS:
        if m not in models_to_try:
            models_to_try.append(m)

    last_err: Optional[Exception] = None

    for m in models_to_try:
        payload: Dict[str, Any] = {
            "model": m,
            "messages": [
                {"role": "system", "content": system_prompt or ""},
                {"role": "user", "content": prompt},
            ],
            "temperature": float(temperature),
        }
        if max_tokens is not None:
            payload["max_tokens"] = int(max_tokens)

        for attempt in range(retries + 1):
            try:
                return _request_once(payload, timeout=timeout)
            except (requests.Timeout, requests.ConnectionError) as e:
                last_err = e
                # network/transient: retry
            except LLMHTTPError as e:
                last_err = e
                msg = str(e)
                # if model is decommissioned, break to try the next model immediately
                if _is_decommissioned(msg):
                    break
                # retry only on rate limits / transient 5xx
                if not _should_retry(msg):
                    raise

            if attempt < retries:
                time.sleep(backoff_base ** attempt)
        # try next model
    # Exhausted all models/retries
    raise LLMHTTPError(f"LLM request failed for all models {models_to_try}: {last_err}")
