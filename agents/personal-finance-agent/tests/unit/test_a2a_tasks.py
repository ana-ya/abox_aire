from fastapi.testclient import TestClient

import app.api as api_module


client = TestClient(api_module.app)


def test_a2a_task_lifecycle(monkeypatch) -> None:
    async def fake_run_agent(prompt: str, session_id: str) -> str:
        return f"processed: {prompt}"

    monkeypatch.setattr(api_module, "_run_agent", fake_run_agent)

    response = client.post(
        "/a2a/tasks",
        json={
            "skill_id": "budget-planning",
            "input": "Calculate monthly budget for income 4200 with rent 1300.",
        },
    )

    assert response.status_code == 200
    task = response.json()
    assert task["status"]["state"] == "submitted"

    follow_up = client.get(f"/a2a/tasks/{task['id']}")
    assert follow_up.status_code == 200
    updated = follow_up.json()
    assert updated["status"]["state"] == "completed"
    assert updated["result"]["skill_id"] == "budget-planning"
