# assistant-agent

Minimal top-level assistant agent that discovers the existing `personal-finance-agent`, reads its Agent Card, submits a finance task, polls the task lifecycle, and prints the final result.

## Architecture

```text
assistant-agent
    -> Agent Card discovery
    -> A2A task request
    -> personal-finance-agent
    -> MCP tools
    -> personal-finance-mcp
```

## Discovery

The assistant agent fetches the existing finance agent card from:

```text
/.well-known/agent.json
```

It then reads:

- agent name
- discovered skills
- task endpoint metadata

## Task Communication

The assistant agent:

1. fetches the Agent Card
2. selects a finance skill
3. submits a task to `POST /a2a/tasks`
4. polls `GET /a2a/tasks/{task_id}`
5. prints status transitions until `completed` or `failed`

Task states used:

- `submitted`
- `working`
- `completed`
- `failed`

## Local Run

Start the existing finance agent first:

```bash
cd agents/personal-finance-agent
uvicorn app.api:app --host 0.0.0.0 --port 8080
```

Then run the assistant agent:

```bash
cd agents/assistant-agent
python orchestrator/client.py
```

You can also point to another environment:

```bash
export PERSONAL_FINANCE_AGENT_URL=http://personal-finance-agent:8080
python orchestrator/client.py
```

## Verification

Check discovery:

```bash
curl http://localhost:8080/.well-known/agent.json
```

Run the assistant agent:

```bash
python orchestrator/client.py
```

Expected output includes:

- discovered agent name
- discovered skills
- task id
- task status transitions
- final response from `personal-finance-agent`

## Example Files

Example request and response files are written to:

```text
agents/assistant-agent/examples/
├── task-request.json
└── task-response.json
```

## Run Against abox

If the agent is reachable in-cluster or through a forwarded service:

```bash
export PERSONAL_FINANCE_AGENT_URL=http://personal-finance-agent:8080
python orchestrator/client.py
```
