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
    model="gemini-2.5-flash",
    instruction="""
    You are a personal finance assistant.

    Use the connected MCP tools for all finance operations.
    Do not list tools unless you actually call or inspect them.
    Do not invent tool names or financial results.
    """,
    tools=[mcp_toolset],
)

app = root_agent