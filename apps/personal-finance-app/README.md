# Personal Finance MCP App

Simple Streamlit UI for a personal finance demo that sends user inputs to an ADK agent. The UI does not call MCP directly and does not perform finance calculations locally.

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

```bash
cd apps/personal-finance-app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ADK_AGENT_URL=http://localhost:8080
streamlit run app.py
```

## Notes

- Default `ADK_AGENT_URL` is `http://localhost:8080`.
- The UI builds a natural-language prompt and sends it to the ADK agent.
- The ADK agent is expected to use MCP tools on the backend.
