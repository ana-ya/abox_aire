import os
from typing import Any

import requests


DEFAULT_AGENT_URL = "http://localhost:8080"
REQUEST_TIMEOUT_SECONDS = 30


def _normalize_response(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "response": str(payload.get("response", "")).strip(),
        "session_id": payload.get("session_id"),
        "known_fields": payload.get("known_fields", {}) or {},
        "missing_fields": payload.get("missing_fields", []) or [],
        "needs_more_info": bool(payload.get("needs_more_info", False)),
        "messages": payload.get("messages", []) or [],
    }


def ask_agent(
    prompt: str,
    *,
    session_id: str | None = None,
    context: dict[str, Any] | None = None,
    messages: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    base_url = os.getenv("ADK_AGENT_URL", DEFAULT_AGENT_URL).rstrip("/")
    ask_url = f"{base_url}/ask"
    payload: dict[str, Any] = {"prompt": prompt}

    if session_id:
        payload["session_id"] = session_id
    if context:
        payload["context"] = context
    if messages:
        payload["messages"] = messages

    try:
        response = requests.post(
            ask_url,
            json=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.exceptions.Timeout:
        return {
            "response": (
                "The ADK agent request timed out after "
                f"{REQUEST_TIMEOUT_SECONDS} seconds. "
                f"Check whether the agent is running and reachable at `{ask_url}`."
            ),
            "session_id": session_id,
            "known_fields": context.get("known_fields", {}) if context else {},
            "missing_fields": context.get("missing_fields", []) if context else [],
            "needs_more_info": True,
            "messages": messages or [],
        }
    except requests.exceptions.ConnectionError:
        return {
            "response": (
                "The ADK agent is unavailable. Start the agent and verify "
                f"`ADK_AGENT_URL` points to the correct service. Current value: `{base_url}`."
            ),
            "session_id": session_id,
            "known_fields": context.get("known_fields", {}) if context else {},
            "missing_fields": context.get("missing_fields", []) if context else [],
            "needs_more_info": True,
            "messages": messages or [],
        }
    except requests.exceptions.HTTPError as exc:
        error_body = exc.response.text.strip() or "no response body"
        try:
            payload = exc.response.json()
            detail = payload.get("detail")
            if detail:
                error_body = str(detail)
        except ValueError:
            pass
        return {
            "response": f"ADK agent returned HTTP {exc.response.status_code}: {error_body}",
            "session_id": session_id,
            "known_fields": context.get("known_fields", {}) if context else {},
            "missing_fields": context.get("missing_fields", []) if context else [],
            "needs_more_info": True,
            "messages": messages or [],
        }
    except requests.RequestException as exc:
        return {
            "response": f"Request to the ADK agent failed: {exc}",
            "session_id": session_id,
            "known_fields": context.get("known_fields", {}) if context else {},
            "missing_fields": context.get("missing_fields", []) if context else [],
            "needs_more_info": True,
            "messages": messages or [],
        }

    try:
        response_payload = response.json()
    except ValueError:
        return {
            "response": "ADK agent returned an unreadable response.",
            "session_id": session_id,
            "known_fields": context.get("known_fields", {}) if context else {},
            "missing_fields": context.get("missing_fields", []) if context else [],
            "needs_more_info": True,
            "messages": messages or [],
        }

    return _normalize_response(response_payload)
