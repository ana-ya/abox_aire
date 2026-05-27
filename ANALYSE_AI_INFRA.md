# Analyse AI Infrastructure

## Vin's Questions

| Question | Answer Based On Current Repo | Evidence In Repo | Gap / Recommendation |
|---|---|---|---|
| 1. How could we handle "agent got stuck" scenarios? | Partially supported. Current setup has request timeouts in the UI client, task states in the finance agent, and `/health` checks. | `apps/personal-finance-app/services/agent_client.py`, `agents/personal-finance-agent/app/api.py` | Add task TTLs, stale-task detection, cancellation, retries, and max execution time per task. |
| 2. Any automatic timeout/circuit breaker patterns coming out form this framework? | Only basic timeout/error handling is implemented in app code. There is also policy scaffolding under `infra/`, but not a working circuit-breaker implementation in the core stack. | `apps/personal-finance-app/services/agent_client.py`, `agents/personal-finance-agent/app/api.py`, `infra/` | Add explicit circuit breaker, retry budget, backoff, and failure thresholds at agent or gateway layer. |
| 3. How does kgateway handle model failover? | AgentGateway is installed, but there is no local config proving model failover behavior. | `releases/agentgateway.yaml`, top-level `README.md` | kgateway AI Gateway supports model failover out of the box, but it must be configured explicitly. |
| 4. Can we automatically switch from OpenAI to Claude to local model? | Current `kagent` config uses OpenAI as default, but the repo does not show automatic multi-provider routing or fallback. | `releases/kagent.yaml` | Add provider routing/fallback policy and a normalization layer for model providers. |
| 5. Could we seamlessly handle the response formats form these providers? | There is no shared adapter that normalizes tool calls, JSON mode, streaming events, or usage data across providers. | `agents/personal-finance-agent/app/api.py`, `agents/personal-finance-agent/app/agent.py` | Introduce a provider abstraction layer before claiming seamless multi-provider support. |
| 6. Can we version the agents built form kagent? | Partially. Infrastructure is GitOps/OCI-versioned, and the deployed components are pinned by release tags. | `README.md`, `releases/kagent.yaml`, `releases/agentgateway.yaml` | Good base for versioning; rollout/promotion strategy still needs explicit implementation. |
| 7. Any blue/green or canary deployment patterns for agents? | Flux-based GitOps is present, and `infra/` contains operational scaffolding, but no blue/green or canary rollout manifests are included for agents. | `README.md`, `releases/`, `infra/` | Add rollout tooling such as weighted routes, Argo Rollouts, or Flagger if this is required. |
| 8. What's the fastmcp-python framework mentioned? | It is the Python MCP framework used by the existing `personal-finance-mcp` server. | `kmcp/personal-finance-mcp/README.md` | |
| 9. Is it the easiest path to mcp? | Yes. MCP integration and local development are straightforward. | `kmcp/personal-finance-mcp/README.md`, `kmcp/personal-finance-mcp/src/` | |
| 10. About finops: how much control I can have? | Limited. The core stack does not show deep spend control, token accounting, or budget enforcement. `infra/` adds some operational scaffolding, but not real FinOps controls. | `agents/personal-finance-agent/app/api.py`, `releases/kagent.yaml`, `infra/` | Add explicit usage accounting, spend metrics, and policy enforcement for real FinOps. |
| 11. Token level / per agent level | Not implemented. | | Add instrumentation around model calls and aggregate per-agent metrics. |
| 12. Can I implement custom cost controls? | Yes, but you would need to build them. | `agents/personal-finance-agent/app/api.py` | Add request gating, provider allowlists, per-session limits, and estimated token-cost checks. |
| 13. Per-agent budgets or depth of Token limits | Not present. | `agents/personal-finance-agent/app/api.py` | Add max turns, max tool calls, max LLM calls, or estimated token ceilings per agent/task. |
| 14. vLLM suitable for agents with many back and forth tool calls, or is it better for single shot inference? | vLLM is not integrated. | | It's an open platform question, not something validated by this repo. |
| 15. llm-d's scheduler - helps when agents makes 15 llms calls? | Not present. | | Needs real integration and benchmarking before making claims. |

## What The Repo Clearly Proves

| Area | Current State |
|---|---|
| AI gateway | `agentgateway` is deployed via Flux/OCI. |
| Agent runtime | `kagent` is deployed and configured with OpenAI as default provider. |
| MCP server | `personal-finance-mcp` is implemented in Python with FastMCP. |
| Agent implementation | `personal-finance-agent` is a working ADK-based standalone API. |
| Agent discovery | Agent Card is exposed via Well-Known URI. |
| A2A | Minimal task-based communication is implemented between `assistant-agent` and `personal-finance-agent`. |

## Supporting Infrastructure In Repo

| Area | Current State |
|---|---|
| `infra/` | Contains operational scaffolding and install/policy helpers for optional components such as inventory, governance policies, and Qdrant. It supports the platform story, but it is weaker evidence than the core runtime manifests and agent code. |

## What The Repo Does Not Yet Prove

| Area | Current State |
|---|---|
| Automatic model failover | Not implemented or evidenced in the core stack. |
| Multi-provider automatic switching | Not implemented. |
| Unified provider response normalization | Not implemented. |
| Token accounting / spend tracking | Not implemented. |
| Per-agent budgets | Not implemented. |
| Canary / blue-green for agents | Not implemented. |
| vLLM / llm-d performance for agent loops | Not validated in this setup. |
