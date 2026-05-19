import os
from typing import Any

import requests


DEFAULT_AGENT_URL = "http://localhost:8080"
DEFAULT_USER_ID = "streamlit-user"
REQUEST_TIMEOUT_SECONDS = 30


def _extract_text(payload: Any) -> str | None:
    if isinstance(payload, str) and payload.strip():
        return payload.strip()

    if isinstance(payload, dict):
        parts = payload.get("parts")
        if isinstance(parts, list):
            text_parts = []
            for part in parts:
                if isinstance(part, dict):
                    text = part.get("text")
                    if isinstance(text, str) and text.strip():
                        text_parts.append(text.strip())
            if text_parts:
                return "\n\n".join(text_parts)

        content = payload.get("content")
        extracted = _extract_text(content)
        if extracted:
            return extracted

        preferred_keys = (
            "response",
            "output",
            "answer",
            "result",
            "message",
            "text",
        )
        for key in preferred_keys:
            extracted = _extract_text(payload.get(key))
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


def _extract_response_from_events(events: Any) -> str | None:
    if not isinstance(events, list):
        return _extract_text(events)

    final_responses = []
    for event in events:
        if not isinstance(event, dict):
            continue

        if event.get("author") == "user":
            continue

        actions = event.get("actions") or {}
        if actions.get("skipSummarization") or actions.get("skip_summarization"):
            continue

        content = event.get("content")
        extracted = _extract_text(content)
        if extracted:
            final_responses.append(extracted)

    if final_responses:
        return "\n\n".join(final_responses)

    return _extract_text(events)


def _request_json(
    session: requests.Session,
    method: str,
    url: str,
    *,
    json_payload: dict[str, Any] | None = None,
) -> Any:
    response = session.request(
        method,
        url,
        json=json_payload,
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    return response.json()


def _get_app_name(session: requests.Session, base_url: str) -> str:
    apps = _request_json(session, "GET", f"{base_url}/list-apps")
    if isinstance(apps, list) and apps:
        return str(apps[0])

    if isinstance(apps, dict):
        detailed_apps = apps.get("apps")
        if isinstance(detailed_apps, list) and detailed_apps:
            first_app = detailed_apps[0]
            if isinstance(first_app, dict) and first_app.get("name"):
                return str(first_app["name"])

    raise RuntimeError("No ADK apps were returned by the agent service.")


def ask_agent(prompt: str) -> str:
    base_url = os.getenv("ADK_AGENT_URL", DEFAULT_AGENT_URL).rstrip("/")
    user_id = os.getenv("ADK_AGENT_USER_ID", DEFAULT_USER_ID)

    try:
        with requests.Session() as session:
            app_name = _get_app_name(session, base_url)

            created_session = _request_json(
                session,
                "POST",
                f"{base_url}/apps/{app_name}/users/{user_id}/sessions",
                json_payload={},
            )
            session_id = created_session.get("id")
            if not session_id:
                raise RuntimeError("ADK session creation succeeded without a session ID.")

            run_payload = {
                "appName": app_name,
                "userId": user_id,
                "sessionId": session_id,
                "newMessage": {
                    "role": "user",
                    "parts": [{"text": prompt}],
                },
            }
            events = _request_json(
                session,
                "POST",
                f"{base_url}/run",
                json_payload=run_payload,
            )

    except requests.exceptions.Timeout:
        return (
            "The ADK agent request timed out after "
            f"{REQUEST_TIMEOUT_SECONDS} seconds. "
            "Check whether the agent is running and reachable at "
            f"`{base_url}`."
        )
    except requests.exceptions.ConnectionError:
        return (
            "The ADK agent is unavailable. Start the agent and verify "
            f"`ADK_AGENT_URL` points to the correct service. Current value: `{base_url}`."
        )
    except requests.exceptions.HTTPError as exc:
        response = exc.response
        body = response.text.strip() if response is not None else "no response body"
        status = response.status_code if response is not None else "unknown"
        return f"ADK agent returned HTTP {status}: {body}"
    except ValueError:
        return "ADK agent returned invalid JSON."
    except Exception as exc:
        return f"Unable to talk to the ADK agent: {exc}"

    extracted = _extract_response_from_events(events)
    if extracted:
        return extracted

    return (
        "The ADK agent responded, but no readable text was found in the returned events. "
        "Check the agent response format or inspect the `/run` response body."
    )
