import json
import logging
import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from pydantic import BaseModel, Field

from app.agent import root_agent


logger = logging.getLogger(__name__)

APP_NAME = "personal-finance-agent"
USER_ID = "api-user"
INTENT_BUDGET = "budget_analysis"
INTENT_SAVINGS = "savings_estimation"
INTENT_DEBT = "debt_payoff"
INTENT_TARGET = "target_purchase_timeline"
CORE_BUDGET_FIELDS = [
    "monthly_income",
    "rent",
    "food",
    "transport",
    "subscriptions",
    "entertainment",
]
DEBT_FIELDS = [
    "debt_amount",
    "annual_interest_rate",
    "monthly_debt_payment",
]
OPTIONAL_FIELDS = ["savings_goal", "target_purchase_amount"]
TEXT_FIELDS = ["target_purchase_item"]
CANONICAL_FIELDS = CORE_BUDGET_FIELDS + OPTIONAL_FIELDS + DEBT_FIELDS + TEXT_FIELDS
FIELD_LABELS = {
    "monthly_income": "monthly income",
    "rent": "rent or housing",
    "food": "food",
    "transport": "transport",
    "subscriptions": "subscriptions",
    "entertainment": "entertainment or variable spending",
    "savings_goal": "savings goal",
    "debt_amount": "debt amount",
    "annual_interest_rate": "annual interest rate",
    "monthly_debt_payment": "monthly debt payment",
    "target_purchase_item": "target purchase item",
    "target_purchase_amount": "target purchase or car goal amount",
}
FIELD_PATTERNS = {
    "monthly_income": [
        r"monthly_income\s*[:=]\s*\$?([0-9]+(?:\.[0-9]+)?)",
        r"(?:monthly income|income|earn|salary|bring in|make)[^\d]{0,20}\$?([0-9]+(?:\.[0-9]+)?)",
    ],
    "rent": [
        r"rent\s*[:=]\s*\$?([0-9]+(?:\.[0-9]+)?)",
        r"(?:rent|housing|mortgage)[^\d]{0,20}\$?([0-9]+(?:\.[0-9]+)?)",
    ],
    "food": [
        r"food\s*[:=]\s*\$?([0-9]+(?:\.[0-9]+)?)",
        r"(?:food|groceries|grocery)[^\d]{0,20}\$?([0-9]+(?:\.[0-9]+)?)",
    ],
    "transport": [
        r"transport\s*[:=]\s*\$?([0-9]+(?:\.[0-9]+)?)",
        r"(?:transport|transportation|commute|gas|transit)[^\d]{0,20}\$?([0-9]+(?:\.[0-9]+)?)",
    ],
    "subscriptions": [
        r"subscriptions\s*[:=]\s*\$?([0-9]+(?:\.[0-9]+)?)",
        r"subscription[s]?[^\d]{0,20}\$?([0-9]+(?:\.[0-9]+)?)",
    ],
    "entertainment": [
        r"entertainment\s*[:=]\s*\$?([0-9]+(?:\.[0-9]+)?)",
        r"(?:entertainment|other expenses|other spending|variable spending|fun money|shopping)[^\d]{0,20}\$?([0-9]+(?:\.[0-9]+)?)",
    ],
    "savings_goal": [
        r"savings_goal\s*[:=]\s*\$?([0-9]+(?:\.[0-9]+)?)",
        r"(?:savings goal|save each month|save monthly)[^\d]{0,20}\$?([0-9]+(?:\.[0-9]+)?)",
    ],
    "debt_amount": [
        r"debt_amount\s*[:=]\s*\$?([0-9]+(?:\.[0-9]+)?)",
        r"(?:debt amount|debt balance|owe|debt is)[^\d]{0,20}\$?([0-9]+(?:\.[0-9]+)?)",
    ],
    "annual_interest_rate": [
        r"annual_interest_rate\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)",
        r"(?:annual interest rate|interest rate|apr)[^\d]{0,20}([0-9]+(?:\.[0-9]+)?)\s*%?",
    ],
    "monthly_debt_payment": [
        r"monthly_debt_payment\s*[:=]\s*\$?([0-9]+(?:\.[0-9]+)?)",
        r"(?:monthly debt payment|debt payment|minimum payment|pay toward debt)[^\d]{0,20}\$?([0-9]+(?:\.[0-9]+)?)",
    ],
    "target_purchase_amount": [
        r"target_purchase_amount\s*[:=]\s*\$?([0-9]+(?:\.[0-9]+)?)",
        r"(?:car goal|car fund|car purchase|target purchase|purchase goal|buy a car|save for a car)[^\d]{0,20}\$?([0-9]+(?:\.[0-9]+)?)",
    ],
}
TARGET_PURCHASE_PATTERNS = [
    (r"car costs?\s+\$?([0-9]+(?:[.,][0-9]+)?k?)", "car"),
    (r"car is\s+\$?([0-9]+(?:[.,][0-9]+)?k?)", "car"),
    (r"i want a car for\s+\$?([0-9]+(?:[.,][0-9]+)?k?)", "car"),
    (r"save for a car\s+\$?([0-9]+(?:[.,][0-9]+)?k?)", "car"),
]
NO_DEBT_PATTERNS = [
    r"\bno debt\b",
    r"\b0 debt\b",
    r"\bdebt is 0\b",
    r"\bi don't have debt\b",
    r"\bi do not have debt\b",
    r"\bdebt free\b",
]
UNKNOWN_SAVINGS_PATTERNS = [
    r"don't know (?:my )?savings goal",
    r"do not know (?:my )?savings goal",
    r"not sure (?:about )?(?:my )?savings goal",
]
INTENT_PATTERNS = {
    INTENT_DEBT: [
        "debt payoff",
        "pay off debt",
        "debt plan",
        "debt analysis",
    ],
    INTENT_TARGET: [
        "car",
        "target purchase",
        "purchase timeline",
        "buy a car",
        "save for a car",
    ],
    INTENT_SAVINGS: [
        "savings",
        "save more",
        "save money",
        "savings estimate",
    ],
    INTENT_BUDGET: [
        "budget",
        "budgeting",
        "spending plan",
        "monthly plan",
    ],
}

app = FastAPI(title="Personal Finance Agent API")
session_service = InMemorySessionService()
runner = Runner(
    app_name=APP_NAME,
    agent=root_agent,
    session_service=session_service,
)
conversation_sessions: dict[str, dict[str, Any]] = {}
a2a_tasks: dict[str, dict[str, Any]] = {}


class ChatMessage(BaseModel):
    role: str
    content: str


class ConversationContext(BaseModel):
    known_fields: dict[str, Any] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)


class AskRequest(BaseModel):
    prompt: str
    session_id: str | None = None
    context: ConversationContext | None = None
    messages: list[ChatMessage] = Field(default_factory=list)


class AskResponse(BaseModel):
    response: str
    session_id: str
    known_fields: dict[str, Any]
    missing_fields: list[str]
    needs_more_info: bool
    messages: list[ChatMessage]


class A2ATaskRequest(BaseModel):
    skill_id: str
    input: str
    context_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _build_base_url(request: Request) -> str:
    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    if forwarded_proto and forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}"
    return str(request.base_url).rstrip("/")


def _build_agent_card(request: Request) -> dict[str, Any]:
    base_url = _build_base_url(request)
    return {
        "name": "Personal Finance Agent",
        "description": (
            "Conversational personal finance agent for budgeting, savings planning, "
            "debt payoff guidance, and target purchase timelines. It orchestrates "
            "finance calculations through MCP tools."
        ),
        "version": "0.1.0",
        "url": base_url,
        "provider": {
            "organization": "abox_aire",
            "url": base_url,
        },
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": True,
            "taskLifecycle": True,
        },
        "endpoints": {
            "agentCard": f"{base_url}/.well-known/agent-card.json",
            "taskCreate": f"{base_url}/a2a/tasks",
            "taskGet": f"{base_url}/a2a/tasks/{{task_id}}",
            "ask": f"{base_url}/ask",
        },
        "defaultInputModes": ["text/plain", "application/json"],
        "defaultOutputModes": ["text/plain", "application/json"],
        "skills": [
            {
                "id": "budget-planning",
                "name": "Budget Planning",
                "description": "Builds a monthly budget from income and recurring expenses.",
                "tags": ["budget", "personal-finance", "monthly-planning"],
                "examples": [
                    "Help me build a monthly budget.",
                    "I earn 3500 and want to understand my spending plan.",
                ],
                "inputModes": ["text/plain", "application/json"],
                "outputModes": ["text/plain", "application/json"],
            },
            {
                "id": "savings-estimation",
                "name": "Savings Estimation",
                "description": "Estimates potential monthly savings from the user's budget.",
                "tags": ["savings", "financial-planning"],
                "examples": [
                    "How much can I save each month?",
                    "Can I save for a car with my current spending?",
                ],
                "inputModes": ["text/plain", "application/json"],
                "outputModes": ["text/plain", "application/json"],
            },
            {
                "id": "debt-payoff",
                "name": "Debt Payoff Guidance",
                "description": "Analyzes debt payoff scenarios when debt details are available.",
                "tags": ["debt", "payoff", "apr"],
                "examples": [
                    "Help me plan my debt payoff.",
                    "I owe 10000 at 18% APR and pay 400 monthly.",
                ],
                "inputModes": ["text/plain", "application/json"],
                "outputModes": ["text/plain", "application/json"],
            },
            {
                "id": "target-purchase-timeline",
                "name": "Target Purchase Timeline",
                "description": "Estimates how long it may take to save toward a target purchase such as a car.",
                "tags": ["goal", "car", "purchase", "timeline"],
                "examples": [
                    "How fast can I buy a car?",
                    "I want a car for 20k. How long will it take to save for it?",
                ],
                "inputModes": ["text/plain", "application/json"],
                "outputModes": ["text/plain", "application/json"],
            },
        ],
        "supportsAuthenticatedExtendedCard": False,
    }


def _extract_text_from_content(content: types.Content | None) -> str:
    if not content or not content.parts:
        return ""
    return "\n\n".join(
        part.text.strip() for part in content.parts if part.text and part.text.strip()
    )


def _extract_final_response(events: list[Any]) -> str:
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


def _normalize_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace("$", "").replace("%", "").strip().lower()
        multiplier = 1.0
        if cleaned.endswith("k"):
            multiplier = 1000.0
            cleaned = cleaned[:-1]
        cleaned = cleaned.replace(",", "")
        if not cleaned:
            return None
        try:
            return float(cleaned) * multiplier
        except ValueError:
            return None
    return None


def _extract_fields_from_text(text: str) -> dict[str, Any]:
    extracted: dict[str, Any] = {}
    for field_name, patterns in FIELD_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            value = _normalize_number(match.group(1))
            if value is not None:
                extracted[field_name] = value
                break
    lowered = text.lower()
    for pattern, item_name in TARGET_PURCHASE_PATTERNS:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if not match:
            continue
        amount = _normalize_number(match.group(1))
        if amount is not None:
            extracted["target_purchase_item"] = item_name
            extracted["target_purchase_amount"] = amount
            break
    return extracted


def _merge_known_fields(*sources: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for source in sources:
        for key, value in source.items():
            if key not in CANONICAL_FIELDS:
                continue
            if key in TEXT_FIELDS:
                if isinstance(value, str) and value.strip():
                    merged[key] = value.strip().lower()
                continue
            normalized = _normalize_number(value)
            if normalized is not None:
                merged[key] = normalized
    return merged


def _detect_no_debt(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in NO_DEBT_PATTERNS)


def _detect_unknown_savings_goal(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in UNKNOWN_SAVINGS_PATTERNS)


def _normalize_business_rules(
    known_fields: dict[str, Any],
    messages: list[dict[str, str]],
    explicit_no_debt: bool,
) -> dict[str, Any]:
    normalized = dict(known_fields)
    if explicit_no_debt:
        normalized["debt_amount"] = 0.0
        normalized["annual_interest_rate"] = 0.0
        normalized["monthly_debt_payment"] = 0.0

    if normalized.get("debt_amount") == 0:
        normalized.setdefault("annual_interest_rate", 0.0)
        normalized.setdefault("monthly_debt_payment", 0.0)

    for message in messages:
        if message["role"] != "user":
            continue
        if _detect_unknown_savings_goal(message["content"]):
            normalized.pop("savings_goal", None)
            break

    return normalized


def _detect_intent(prompt: str, messages: list[dict[str, str]]) -> str:
    texts = [prompt.lower()] + [
        message["content"].lower()
        for message in reversed(messages)
        if message["role"] == "user"
    ]
    ordered_intents = [INTENT_DEBT, INTENT_TARGET, INTENT_SAVINGS, INTENT_BUDGET]
    for text in texts:
        for intent in ordered_intents:
            if any(term in text for term in INTENT_PATTERNS[intent]):
                return intent
    return INTENT_BUDGET


def _compute_missing_fields(
    known_fields: dict[str, Any],
    current_intent: str,
    asked_fields: set[str],
) -> list[str]:
    missing_fields = [field for field in CORE_BUDGET_FIELDS if field not in known_fields]

    if current_intent in (INTENT_SAVINGS, INTENT_TARGET):
        if "entertainment" not in known_fields and all(
            field in known_fields for field in CORE_BUDGET_FIELDS if field != "entertainment"
        ):
            missing_fields = [field for field in missing_fields if field != "entertainment"]
            known_fields["entertainment"] = 0.0
    elif "entertainment" in missing_fields and "entertainment" in asked_fields:
        missing_fields = [field for field in missing_fields if field != "entertainment"]
        known_fields["entertainment"] = 0.0

    debt_amount = known_fields.get("debt_amount")
    debt_required = current_intent == INTENT_DEBT or (
        debt_amount is not None and debt_amount > 0
    )
    if debt_required and debt_amount is None:
        missing_fields.append("debt_amount")

    if debt_required and debt_amount is not None and debt_amount > 0:
        for field in ("annual_interest_rate", "monthly_debt_payment"):
            if field not in known_fields:
                missing_fields.append(field)

    if current_intent == INTENT_TARGET and "target_purchase_amount" not in known_fields:
        missing_fields.append("target_purchase_amount")

    return missing_fields


def _has_enough_information(
    known_fields: dict[str, Any],
    current_intent: str,
) -> bool:
    if current_intent == INTENT_TARGET:
        return all(field in known_fields for field in CORE_BUDGET_FIELDS) and (
            "target_purchase_amount" in known_fields
        )

    if current_intent == INTENT_DEBT:
        debt_amount = known_fields.get("debt_amount")
        if debt_amount == 0:
            return all(field in known_fields for field in CORE_BUDGET_FIELDS)
        return (
            debt_amount is not None
            and debt_amount > 0
            and "annual_interest_rate" in known_fields
            and "monthly_debt_payment" in known_fields
        )

    return all(field in known_fields for field in CORE_BUDGET_FIELDS)


def _merge_messages(
    stored_messages: list[dict[str, str]],
    request_messages: list[ChatMessage],
) -> list[dict[str, str]]:
    merged = [dict(message) for message in stored_messages]
    for message in request_messages:
        candidate = {"role": message.role, "content": message.content.strip()}
        if not candidate["content"]:
            continue
        if candidate not in merged:
            merged.append(candidate)
    return merged


def _ensure_runner_session(session_id: str) -> None:
    existing_session = session_service.get_session_sync(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
    )
    if existing_session:
        return
    session_service.create_session_sync(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
    )


def _conversation_excerpt(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    if not messages:
        return []
    return messages[-6:]


def _build_agent_prompt(
    current_prompt: str,
    known_fields: dict[str, Any],
    missing_fields: list[str],
    current_intent: str,
    needs_more_info: bool,
    recent_history: list[dict[str, str]],
    assumptions: list[str],
) -> str:
    return f"""
You are supporting the Personal Finance MCP App.

Current intent:
{current_intent}

Structured known financial fields:
{json.dumps(known_fields, indent=2, sort_keys=True)}

Structured missing fields:
{json.dumps(missing_fields, indent=2)}

Structured assumptions:
{json.dumps(assumptions, indent=2)}

Recent conversation history:
{json.dumps(recent_history, indent=2)}

Latest user message:
{current_prompt}

Rules:
- The backend state above is the source of truth.
- Do not ask again for any field that is not listed in structured missing fields.
- Do not invent numbers or assume missing values.
- If structured missing fields is empty, use the MCP tools and produce the final recommendation.
- If structured missing fields is not empty, ask only for those fields in concise conversational wording.
- Savings goal is optional unless the user volunteers it. Do not insist on it.
- If debt amount is zero, do not ask for interest rate or monthly debt payment.
- If assumptions are provided, keep them explicit in the final answer.

Required action:
{"Ask for the structured missing fields only." if needs_more_info else "Use MCP tools now and produce the final analysis."}
""".strip()


async def _run_agent(prompt: str, session_id: str) -> str:
    _ensure_runner_session(session_id)
    message = types.Content(role="user", parts=[types.Part(text=prompt)])
    events = []
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=message,
    ):
        events.append(event)
    response_text = _extract_final_response(events)
    if response_text:
        return response_text
    raise RuntimeError("Agent execution completed without a final text response.")


def _log_debug_state(
    *,
    session_id: str,
    extracted_fields: dict[str, float],
    normalized_fields: dict[str, float],
    missing_fields: list[str],
    current_intent: str,
) -> None:
    logger.info(
        "elicitation_state session_id=%s extracted_fields=%s normalized_fields=%s missing_fields=%s current_intent=%s",
        session_id,
        extracted_fields,
        normalized_fields,
        missing_fields,
        current_intent,
    )


def _new_status(state: str, message: str) -> dict[str, Any]:
    return {
        "state": state,
        "message": message,
        "timestamp": _utc_now(),
    }


async def _process_a2a_task(task_id: str) -> None:
    task = a2a_tasks[task_id]
    task["history"].append(_new_status("working", "Task is being processed by the finance agent."))
    task["status"] = task["history"][-1]

    try:
        response_text = await _run_agent(task["input"], task["context_id"])
    except Exception as exc:
        logger.exception("A2A task failed")
        task["history"].append(_new_status("failed", f"Task failed: {exc}"))
        task["status"] = task["history"][-1]
        task["result"] = {"error": str(exc)}
        return

    task["result"] = {
        "response": response_text,
        "skill_id": task["skill_id"],
    }
    task["history"].append(_new_status("completed", "Task completed successfully."))
    task["status"] = task["history"][-1]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/.well-known/agent-card.json")
async def well_known_agent_card(request: Request) -> JSONResponse:
    agent_card = _build_agent_card(request)
    return JSONResponse(agent_card, headers={"Cache-Control": "public, max-age=300"})


@app.get("/.well-known/agent.json")
async def legacy_well_known_agent_card(request: Request) -> JSONResponse:
    agent_card = _build_agent_card(request)
    return JSONResponse(agent_card, headers={"Cache-Control": "public, max-age=300"})


@app.get("/agent-card")
async def agent_card(request: Request) -> JSONResponse:
    agent_card = _build_agent_card(request)
    return JSONResponse(agent_card, headers={"Cache-Control": "public, max-age=300"})


@app.post("/a2a/tasks")
async def create_a2a_task(
    req: A2ATaskRequest,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    if not req.input.strip():
        raise HTTPException(status_code=400, detail="Task input must not be empty.")

    task_id = str(uuid4())
    context_id = req.context_id or str(uuid4())
    task = {
        "id": task_id,
        "context_id": context_id,
        "skill_id": req.skill_id,
        "input": req.input,
        "metadata": req.metadata,
        "history": [_new_status("submitted", "Task received by the finance agent.")],
        "status": _new_status("submitted", "Task received by the finance agent."),
        "result": None,
    }
    a2a_tasks[task_id] = task
    task["status"] = task["history"][0]
    background_tasks.add_task(_process_a2a_task, task_id)
    return JSONResponse(task)


@app.get("/a2a/tasks/{task_id}")
async def get_a2a_task(task_id: str) -> JSONResponse:
    task = a2a_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return JSONResponse(task)


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    prompt = req.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt must not be empty.")

    session_id = req.session_id or str(uuid4())
    stored = conversation_sessions.setdefault(
        session_id,
        {
            "messages": [],
            "known_fields": {},
            "missing_fields": [],
            "current_intent": INTENT_BUDGET,
            "asked_fields": set(),
        },
    )

    merged_messages = _merge_messages(stored["messages"], req.messages)
    user_message = {"role": "user", "content": prompt}
    if not merged_messages or merged_messages[-1] != user_message:
        merged_messages.append(user_message)

    request_context = req.context or ConversationContext()
    extracted_from_history: dict[str, Any] = {}
    for message in merged_messages:
        if message["role"] != "user":
            continue
        extracted_from_history.update(_extract_fields_from_text(message["content"]))
    extracted_from_prompt = _extract_fields_from_text(prompt)
    explicit_no_debt = any(
        _detect_no_debt(message["content"])
        for message in merged_messages
        if message["role"] == "user"
    )

    known_fields = _merge_known_fields(
        stored.get("known_fields", {}),
        request_context.known_fields,
        extracted_from_history,
        extracted_from_prompt,
    )
    known_fields = _normalize_business_rules(
        known_fields=known_fields,
        messages=merged_messages,
        explicit_no_debt=explicit_no_debt,
    )
    current_intent = _detect_intent(prompt, merged_messages)
    missing_fields = _compute_missing_fields(
        known_fields,
        current_intent,
        stored.get("asked_fields", set()),
    )
    needs_more_info = not _has_enough_information(known_fields, current_intent)
    assumptions: list[str] = []
    if known_fields.get("entertainment") == 0 and "entertainment" not in extracted_from_history and "entertainment" not in extracted_from_prompt:
        assumptions.append("Entertainment or other variable spending assumed to be 0.")

    _log_debug_state(
        session_id=session_id,
        extracted_fields=_merge_known_fields(extracted_from_history, extracted_from_prompt),
        normalized_fields=known_fields,
        missing_fields=missing_fields,
        current_intent=current_intent,
    )

    agent_prompt = _build_agent_prompt(
        current_prompt=prompt,
        known_fields=known_fields,
        missing_fields=missing_fields,
        current_intent=current_intent,
        needs_more_info=needs_more_info,
        recent_history=_conversation_excerpt(merged_messages),
        assumptions=assumptions,
    )

    try:
        response_text = await _run_agent(agent_prompt, session_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Agent execution failed")
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {exc}",
        ) from exc

    merged_messages.append({"role": "assistant", "content": response_text})
    stored["messages"] = merged_messages
    stored["known_fields"] = known_fields
    stored["missing_fields"] = missing_fields
    stored["current_intent"] = current_intent
    stored["asked_fields"] = set(stored.get("asked_fields", set())) | set(missing_fields)

    return AskResponse(
        response=response_text,
        session_id=session_id,
        known_fields=known_fields,
        missing_fields=missing_fields,
        needs_more_info=needs_more_info,
        messages=[ChatMessage(**message) for message in merged_messages[-12:]],
    )
