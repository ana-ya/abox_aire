import os
from typing import Any

import requests


DEFAULT_AGENT_URL = "http://localhost:8080"
REQUEST_TIMEOUT_SECONDS = 30


def _extract_text(payload: Any) -> str | None:
    if isinstance(payload, str) and payload.strip():
        return payload.strip()

    if isinstance(payload, dict):
        for key in ("response", "output", "answer", "result", "message", "text"):
            value = payload.get(key)
            extracted = _extract_text(value)
            if extracted:
                return extracted

        for value in payload.values():
            extracted = _extract_text(value)
            if extracted:
                return extracted

    if isinstance(payload, list):
        parts = []
        for item in payload:
            extracted = _extract_text(item)
            if extracted:
                parts.append(extracted)
        if parts:
            return "\n\n".join(parts)

    return None


def ask_agent(prompt: str) -> str:
    base_url = os.getenv("ADK_AGENT_URL", DEFAULT_AGENT_URL).rstrip("/")
    ask_url = f"{base_url}/ask"

    try:
        response = requests.post(
            ask_url,
            json={"prompt": prompt},
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.exceptions.Timeout:
        return (
            "The ADK agent request timed out after "
            f"{REQUEST_TIMEOUT_SECONDS} seconds. "
            f"Check whether the agent is running and reachable at `{ask_url}`."
        )
    except requests.exceptions.ConnectionError:
        return (
            "The ADK agent is unavailable. Start the agent and verify "
            f"`ADK_AGENT_URL` points to the correct service. Current value: `{base_url}`."
        )
    except requests.exceptions.HTTPError as exc:
        error_body = ""
        try:
            payload = exc.response.json()
            error_body = _extract_text(payload) or str(payload)
        except ValueError:
            error_body = exc.response.text.strip() or "no response body"
        return f"ADK agent returned HTTP {exc.response.status_code}: {error_body}"
    except requests.RequestException as exc:
        return f"Request to the ADK agent failed: {exc}"

    try:
        payload = response.json()
    except ValueError:
        text = response.text.strip()
        if text:
            return text
        return "ADK agent returned an unreadable response."

    extracted = _extract_text(payload)
    if extracted:
        return extracted

    return str(payload)
