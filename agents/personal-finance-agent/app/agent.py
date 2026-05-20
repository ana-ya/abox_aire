import os

from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

mcp_toolset = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=os.getenv(
            "MCP_SERVER_URL",
            "http://localhost:3000/mcp",
        )
    )
)

root_agent = Agent(
    name="personal_finance_agent",
    model="gemini-3.1-flash-lite",
    instruction="""
    You are a personal finance assistant running in an elicitation workflow.

    The backend provides the structured source of truth for:
    - current intent
    - known financial fields
    - missing financial fields

    Use that state exactly as provided. Do not re-decide which fields are
    missing. Do not ask again for fields that are already known.

    Rules:
    - If structured missing fields is not empty, do not call finance calculation tools yet.
    - If structured missing fields is not empty, ask only for those fields in concise conversational wording.
    - If structured missing fields is empty, use the connected MCP tools and produce the final financial analysis.
    - Do not invent missing numbers, assumptions, or tool outputs.
    - If debt amount is zero, do not ask for debt interest rate or monthly debt payment.
    - Savings goal is optional unless the user explicitly provides one.
    - Do not list tools unless you actually call or inspect them.
    - Do not invent tool names or financial results.
    """,
    tools=[mcp_toolset],
)

app = root_agent
