import logging
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from pydantic import BaseModel

from app.agent import root_agent


logger = logging.getLogger(__name__)

APP_NAME = "personal-finance-agent"

app = FastAPI(title="Personal Finance Agent API")


class AskRequest(BaseModel):
    prompt: str


class AskResponse(BaseModel):
    response: str


def _extract_text_from_content(content: types.Content | None) -> str:
    if not content or not content.parts:
        return ""

    text_parts: list[str] = []
    for part in content.parts:
        if part.text and part.text.strip():
            text_parts.append(part.text.strip())

    return "\n\n".join(text_parts)


def _extract_final_response(events: list) -> str:
    responses: list[str] = []

    for event in events:
        if getattr(event, "author", None) == "user":
            continue

        if not event.is_final_response():
            continue

        text = _extract_text_from_content(getattr(event, "content", None))
        if text:
            responses.append(text)

    if responses:
        return "\n\n".join(responses)

    for event in reversed(events):
        text = _extract_text_from_content(getattr(event, "content", None))
        if text:
            return text

    return ""


async def _run_agent(prompt: str) -> str:
    session_service = InMemorySessionService()
    runner = Runner(
        app_name=APP_NAME,
        agent=root_agent,
        session_service=session_service,
    )

    user_id = "api-user"
    session_id = str(uuid4())

    await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )

    message = types.Content(
        role="user",
        parts=[types.Part(text=prompt)],
    )

    events = []
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=message,
    ):
        events.append(event)

    response_text = _extract_final_response(events)
    if response_text:
        return response_text

    raise RuntimeError("Agent execution completed without a final text response.")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    prompt = req.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt must not be empty.")

    try:
        response_text = await _run_agent(prompt)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Agent execution failed")
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {exc}",
        ) from exc

    return AskResponse(response=response_text)
