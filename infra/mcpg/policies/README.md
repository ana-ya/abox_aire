# MCP Security Governance

MCP Security Governance was deployed as a governance layer for MCP infrastructure in the existing `abox` cluster.

## Purpose

MCP servers expose tools that can be used by agents to interact with Kubernetes, APIs, external systems and other infrastructure components.

This component is used to add visibility and governance for MCP-related resources, including:

- MCP servers
- remote MCP servers
- kagent agents
- AgentGateway-related resources
- governance policies
- governance evaluations

## Upstream

https://github.com/techwithhuz/mcp-security-governance

The upstream source code is not vendored into this repository. It is used as an external dependency during installation.

## Installed Namespace

```bash
mcp-governance
```

## Installation

Clone the upstream repository temporarily:

```bash
git clone https://github.com/techwithhuz/mcp-security-governance.git
cd mcp-security-governance
```

Install CRDs:

```bash
kubectl apply -f charts/mcp-governance/crds/
```

Install Helm chart:

```bash
helm upgrade --install mcp-governance ./charts/mcp-governance \
  -n mcp-governance \
  --create-namespace
```

## Local Images for kind

The Helm chart uses local images:

```text
localhost/mcp-governance-controller:latest
localhost/mcp-governance-dashboard:latest
```

For a `kind` cluster, these images must be built locally and loaded into the cluster.

Build controller image:

```bash
docker build -t localhost/mcp-governance-controller:latest \
  -f controller/Dockerfile \
  controller
```

Build dashboard image:

```bash
docker build -t localhost/mcp-governance-dashboard:latest \
  -f dashboard/Dockerfile \
  dashboard
```

Load images into the `abox` kind cluster:

```bash
kind load docker-image localhost/mcp-governance-controller:latest --name abox
kind load docker-image localhost/mcp-governance-dashboard:latest --name abox
```

Restart deployments:

```bash
kubectl rollout restart deploy -n mcp-governance
```

## Verify Deployment

```bash
kubectl get pods -n mcp-governance
kubectl get svc -n mcp-governance
kubectl get deploy -n mcp-governance
```

Expected pods:

```text
mcp-governance-controller   Running
mcp-governance-dashboard    Running
```

Expected services:

```text
mcp-governance-controller   ClusterIP   8090/TCP
mcp-governance-dashboard    NodePort    3000/TCP
```

## Access Dashboard

If local port `3000` is already used, use `3001`:

```bash
kubectl port-forward -n mcp-governance svc/mcp-governance-dashboard 3001:3000
```

Open:

```text
http://localhost:3001
```

## Apply Governance Policy

A sample governance policy can be stored in this repository under:

```text
infra/mcpg/policies/governance-policy.yaml
```

Apply policies:

```bash
kubectl apply -f infra/mcpg/policies/
```

Verify policies and evaluations:

```bash
kubectl get mcpgovernancepolicies -A
kubectl get governanceevaluations -A
```

## Existing AI Resources

The governance layer is deployed on top of the existing `abox` AI infrastructure.

Useful checks:

```bash
kubectl get agents.kagent.dev -n kagent
kubectl get mcpservers.kagent.dev -n kagent
kubectl get remotemcpservers.kagent.dev -n kagent
kubectl get modelconfigs.kagent.dev -n kagent
```

## Troubleshooting

### ErrImageNeverPull or Image Not Present

If pods fail with image errors, verify that local images exist:

```bash
docker images | grep mcp-governance
```

Then load them into kind:

```bash
kind load docker-image localhost/mcp-governance-controller:latest --name abox
kind load docker-image localhost/mcp-governance-dashboard:latest --name abox
```

Restart deployments:

```bash
kubectl rollout restart deploy -n mcp-governance
```

### Port 3000 Already Used

Use another local port:

```bash
kubectl port-forward -n mcp-governance svc/mcp-governance-dashboard 3001:3000
```

## Repository Layout

Recommended files to commit into this repository:

```text
infra/mcpg/
├── README.md
├── install.sh
└── policies/
    └── governance-policy.yaml
```
