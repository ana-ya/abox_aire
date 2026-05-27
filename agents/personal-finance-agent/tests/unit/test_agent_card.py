from fastapi.testclient import TestClient

from app.api import app


client = TestClient(app)


def test_agent_card_well_known_endpoint() -> None:
    response = client.get("/.well-known/agent-card.json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Personal Finance Agent"
    assert payload["url"] == "http://testserver"
    assert payload["endpoints"]["taskCreate"].endswith("/a2a/tasks")
    assert any(skill["id"] == "budget-planning" for skill in payload["skills"])


def test_legacy_agent_card_endpoint() -> None:
    response = client.get("/.well-known/agent.json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Personal Finance Agent"
