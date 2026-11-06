"""One client for every AI provider (DEC-013).

OpenRouter (demo) and Ollama (on premises) both speak the OpenAI chat API, so one
small client serves both. Differences are handled here:
- OpenRouter: a list of models to fall back through, and usage and cost reporting
- Ollama: a single local model, no data leaves the machine

Every call uses temperature 0 and a strict JSON schema for the reply.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass

import httpx

from daleel.core.config import get_settings


@dataclass
class AIReply:
    content: dict
    provider: str
    model: str
    usage: dict
    seconds: float


class AIUnavailable(Exception):
    pass


def complete_json(system: str, user: str, schema: dict, name: str) -> AIReply:
    s = get_settings()
    if s.ai_provider == "off":
        raise AIUnavailable("AI is switched off (AI_PROVIDER=off).")
    if s.ai_provider == "openrouter":
        if not s.openrouter_api_key:
            raise AIUnavailable("No OpenRouter API key is configured.")
        url, key, models = s.openrouter_base_url, s.openrouter_api_key, s.ai_model_list
    else:
        url, key, models = s.ollama_base_url, "ollama", [s.ollama_model]
    body: dict = {
        "model": models[0],
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0,
        "response_format": {"type": "json_schema", "json_schema": {"name": name, "strict": True, "schema": schema}},
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if s.ai_provider == "openrouter":
        body["models"] = models  # automatic fallback, in order
        body["usage"] = {"include": True}
        headers["X-Title"] = "Daleel"
        headers["HTTP-Referer"] = "https://github.com/I-can-do-everything/SBP-Islamic-Banking-RegTech"
    started = time.monotonic()
    last_error = ""
    for attempt in range(3):
        try:
            response = httpx.post(f"{url}/chat/completions", json=body, headers=headers,
                                  timeout=s.ai_timeout_seconds)
        except httpx.HTTPError as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(2 * (attempt + 1))
            continue
        if response.status_code == 429 or response.status_code >= 500:
            last_error = f"HTTP {response.status_code}: {response.text[:200]}"
            time.sleep(3 * (attempt + 1))
            continue
        if response.status_code != 200:
            raise AIUnavailable(f"HTTP {response.status_code}: {response.text[:300]}")
        data = response.json()
        if "choices" not in data or not data["choices"]:
            last_error = f"no choices: {str(data)[:200]}"
            continue
        text = data["choices"][0]["message"].get("content") or ""
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("`").removeprefix("json").strip()
        try:
            content = json.loads(text)
        except json.JSONDecodeError:
            last_error = "reply was not valid JSON"
            continue
        return AIReply(content, s.ai_provider, data.get("model", models[0]), data.get("usage", {}),
                       round(time.monotonic() - started, 2))
    raise AIUnavailable(last_error or "The AI provider did not answer.")
