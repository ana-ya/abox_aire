# Personal Finance MCP App

This Streamlit app is the AI host for the personal finance demo. It does not call MCP directly and it does not perform financial calculations locally. It sends user requests to the standalone ADK agent API, and the agent decides when to use the MCP finance tools.

## Modes

### Finance Planner

The original static workflow is still available:

1. User fills the finance form.
2. Streamlit sends a complete prompt to the agent API.
3. The agent uses MCP tools to generate the final financial response.

### Conversational Financial Intake

This is the elicitation workflow:

1. User starts with incomplete information.
2. Streamlit stores conversation state in `st.session_state`.
3. The agent API returns follow-up questions plus the latest `known_fields` and `missing_fields`.
4. The user answers follow-up questions across multiple turns.
5. Once all required fields are available, the agent uses MCP tools and returns the final recommendation.

## Sampling And Elicitation

Sampling in this project means the LLM generates financial guidance from MCP tool outputs after the tools have been called.

Elicitation means the agent asks for missing financial inputs before calling the calculation tools. The goal is to avoid hallucinated assumptions and only invoke MCP tools when the financial profile is complete.

## Architecture

```text
Streamlit App
  -> Agent API (/ask)
  -> ADK Agent
  -> MCPToolset / MCP Client
  -> personal-finance-mcp
  -> finance tools
```

The finance tools currently exposed by the MCP server include:

- `calculate_monthly_budget`
- `analyze_expenses`
- `debt_payoff_estimate`
- `echo`

## Files

```text
apps/personal-finance-app/
├── app.py
├── services/
│   └── agent_client.py
├── requirements.txt
├── README.md
└── .gitignore
```

## Local Run

Start the MCP server and the standalone agent API first. The Streamlit app expects the agent API to expose:

- `GET /health`
- `POST /ask`

Then run the UI:

```bash
cd apps/personal-finance-app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ADK_AGENT_URL=http://localhost:8080
streamlit run app.py
```

## Kubernetes Notes

- The Streamlit client calls `POST {ADK_AGENT_URL}/ask`.
- Local default is `http://localhost:8080`.
- In Kubernetes, the expected agent service URL is `http://personal-finance-agent:8080`.
- The existing deployment manifests live under `gitlessops/`.

## Notes

- Default `ADK_AGENT_URL` is `http://localhost:8080`.
- The UI sends chat turns and static planner prompts to the agent API.
- The agent is responsible for orchestration and MCP tool usage.
- The MCP server remains the only layer that performs finance calculations.
