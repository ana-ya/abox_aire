import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PERSONAL_FINANCE_AGENT_URL = os.getenv(
    "PERSONAL_FINANCE_AGENT_URL",
    "http://localhost:8080",
).rstrip("/")
WELL_KNOWN_AGENT_CARD_URL = f"{PERSONAL_FINANCE_AGENT_URL}/.well-known/agent.json"
TASK_CREATE_URL = f"{PERSONAL_FINANCE_AGENT_URL}/a2a/tasks"
TASK_POLL_INTERVAL_SECONDS = 1.0
TASK_POLL_TIMEOUT_SECONDS = 60.0
SKILL_KEYWORDS = {
    "budget-planning": {
        "budget",
        "income",
        "rent",
        "food",
        "transport",
        "subscriptions",
        "expense",
        "spending",
        "monthly",
    },
    "savings-estimation": {
        "save",
        "savings",
        "goal",
        "car",
        "purchase",
        "timeline",
    },
    "debt-payoff": {
        "debt",
        "apr",
        "interest",
        "payment",
        "payoff",
        "loan",
    },
    "target-purchase-timeline": {
        "car",
        "purchase",
        "target",
        "timeline",
        "save for",
        "buy",
    },
}


def fetch_agent_card() -> dict[str, Any]:
    payload = _request_json("GET", WELL_KNOWN_AGENT_CARD_URL)
    if "name" not in payload or "skills" not in payload:
        raise RuntimeError("Agent Card is missing required fields.")
    return payload


def pick_skill(agent_card: dict[str, Any], task_input: str) -> dict[str, Any] | None:
    lowered = task_input.lower()
    best_skill = None
    best_score = 0

    for skill in agent_card.get("skills", []):
        skill_id = skill.get("id")
        keywords = SKILL_KEYWORDS.get(skill_id, set())
        score = sum(1 for keyword in keywords if keyword in lowered)
        if score > best_score:
            best_score = score
            best_skill = skill

    if best_score == 0:
        return None
    return best_skill


def create_task(skill: dict[str, Any], task_input: str) -> dict[str, Any]:
    payload = {
        "skill_id": skill["id"],
        "input": task_input,
        "metadata": {
            "source": "assistant-agent",
        },
    }
    return _request_json("POST", TASK_CREATE_URL, payload)


def poll_task(task_id: str) -> dict[str, Any]:
    deadline = time.time() + TASK_POLL_TIMEOUT_SECONDS
    seen_states: set[str] = set()
    last_task: dict[str, Any] | None = None

    while time.time() < deadline:
        task = _request_json("GET", f"{TASK_CREATE_URL}/{task_id}")
        last_task = task
        state = task["status"]["state"]
        if state not in seen_states:
            seen_states.add(state)
            print(f"task status -> {state}")

        if state in {"completed", "failed"}:
            return task

        time.sleep(TASK_POLL_INTERVAL_SECONDS)

    raise TimeoutError(f"Timed out while waiting for task {task_id}. Last task: {last_task}")


def _request_json(method: str, url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=data, headers=headers, method=method)

    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"Request to {url} failed: {exc}") from exc


def save_examples(task_request: dict[str, Any], task_response: dict[str, Any]) -> None:
    examples_dir = Path(__file__).resolve().parents[1] / "examples"
    examples_dir.mkdir(parents=True, exist_ok=True)
    (examples_dir / "task-request.json").write_text(
        json.dumps(task_request, indent=2),
        encoding="utf-8",
    )
    (examples_dir / "task-response.json").write_text(
        json.dumps(task_response, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    task_input = " ".join(sys.argv[1:]).strip()
    if not task_input:
        task_input = (
            "Calculate monthly budget for income 4200 with rent 1300, "
            "food 550, transport 180 and subscriptions 90."
        )

    print(f"discovering agent card from {WELL_KNOWN_AGENT_CARD_URL}")
    agent_card = fetch_agent_card()
    print(f"discovered agent name: {agent_card['name']}")

    skills = agent_card.get("skills", [])
    print("discovered skills:")
    for skill in skills:
        print(f"- {skill['id']}: {skill['name']}")

    skill = pick_skill(agent_card, task_input)
    if skill is None:
        print("selected skill: none")
        print("task rejected: no matching finance skill found for this request")
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason": (
                        "The available remote agent is finance-specific and does not fit "
                        "this task."
                    ),
                    "input": task_input,
                },
                indent=2,
            )
        )
        raise SystemExit(2)

    print(f"selected skill: {skill['id']}")

    task_request = {
        "skill_id": skill["id"],
        "input": task_input,
        "metadata": {"source": "assistant-agent"},
    }
    task = create_task(skill, task_input)
    print(f"task id: {task['id']}")
    print(f"task status -> {task['status']['state']}")

    final_task = poll_task(task["id"])
    save_examples(task_request, final_task)

    print("final response/result:")
    print(json.dumps(final_task.get("result", {}), indent=2))


if __name__ == "__main__":
    main()
