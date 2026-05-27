# personal-finance-agent

This service is the orchestration layer between the Streamlit app and the Personal Finance MCP server. It exposes a standalone FastAPI API and runs the ADK root agent with an MCP toolset connected to `MCP_SERVER_URL`.

## API

The service exposes:

- `GET /health`
- `POST /ask`

`POST /ask` supports conversational elicitation with optional in-memory session context:

```json
{
  "prompt": "I make 3500 a month and need budgeting help.",
  "session_id": "optional-session-id",
  "context": {
    "known_fields": {
      "monthly_income": 3500
    },
    "missing_fields": [
      "rent",
      "food"
    ]
  }
}
```

The response includes:

```json
{
  "response": "I still need your rent, food, and debt details before I can run the finance tools.",
  "session_id": "session-id",
  "known_fields": {
    "monthly_income": 3500
  },
  "missing_fields": [
    "rent",
    "food",
    "transport",
    "subscriptions",
    "entertainment",
    "savings_goal",
    "debt_amount",
    "annual_interest_rate",
    "monthly_debt_payment"
  ],
  "needs_more_info": true
}
```

## Agent Card

This agent also exposes an Agent Card for discovery.

Available endpoints:

- `GET /.well-known/agent-card.json`
- `GET /.well-known/agent.json`
- `GET /agent-card`

Fetch it locally with `curl`:

```bash
curl http://localhost:8080/.well-known/agent-card.json
```

Legacy-compatible path:

```bash
curl http://localhost:8080/.well-known/agent.json
```

Pretty-print with `jq` if installed:

```bash
curl -s http://localhost:8080/.well-known/agent-card.json | jq
```

## Sampling And Elicitation

Sampling in this project means the LLM turns MCP tool outputs into user-facing financial guidance.

Elicitation means the agent first asks for missing required financial fields, avoids inventing numbers, and only invokes the MCP finance tools when the profile is complete.

## Architecture

```text
Streamlit App
  -> Agent API (/ask)
  -> ADK Agent
  -> MCPToolset / MCP Client
  -> personal-finance-mcp
  -> finance tools
```

## Local Run

Install dependencies in the agent environment, set the MCP endpoint, and run the standalone API:

```bash
cd agents/personal-finance-agent
export MCP_SERVER_URL=http://localhost:3000/mcp
uvicorn app.api:app --host 0.0.0.0 --port 8080
```

Then verify the health endpoint and Agent Card:

```bash
curl http://localhost:8080/health
curl http://localhost:8080/.well-known/agent-card.json
```

The Docker command for this service should be:

```bash
uvicorn app.api:app --host 0.0.0.0 --port 8080
```

## Kubernetes Notes

- The Streamlit app should call `http://personal-finance-agent:8080/ask` inside the cluster.
- The MCP server remains a separate service and is not called directly by the UI.
- Existing deployment manifests are under `gitlessops/`.

## Project Structure

```text
personal-finance-agent/
├── app/
│   ├── agent.py
│   ├── api.py
│   └── app_utils/
├── tests/
├── README.md
└── pyproject.toml
```
