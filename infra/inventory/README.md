# Agent Registry Inventory

Integration of Agent Registry Inventory into the existing `abox` AI infrastructure.

## Installed Components

- kagent
- declarative agents
- MCP servers
- model configs
- Agent Registry Inventory

## Upstream

https://github.com/den-vasyliev/agentregistry-inventory

## Installation

Clone upstream repository:

```bash
git clone https://github.com/den-vasyliev/agentregistry-inventory.git
cd agentregistry-inventory
```

Install CRDs:

```bash
kubectl apply -f charts/agentregistry/crds/
```

Install inventory:

```bash
helm install agentregistry-inventory ./charts/agentregistry \
  -n agentregistry \
  --create-namespace
```

## Access UI

```bash
kubectl port-forward -n agentregistry svc/agentregistry-inventory-api 8080:8080
```

Open:

```text
http://localhost:8080
```

## Discovery Configuration

Apply discovery config:

```bash
kubectl apply -f infra/inventory/discoveryconfig.yaml
```

Verify:

```bash
kubectl get discoveryconfigs.agentregistry.dev -A
```

## Discovered Resources

```bash
kubectl get agents.kagent.dev -A
kubectl get mcpservers.kagent.dev -A
kubectl get modelconfigs.kagent.dev -A
```

## Skill Catalogs

The inventory controller did not automatically extract A2A skills from:

```yaml
spec.declarative.a2aConfig.skills
```

Manual `SkillCatalog` resources were created as a workaround.

Apply:

```bash
kubectl apply -f infra/inventory/skillcatalogs/
```

Verify:

```bash
kubectl get skillcatalogs.agentregistry.dev -A
```

## Findings

Successfully discovered:
- agents
- MCP servers
- model configs

Observed limitation:
- automatic extraction of A2A declarative skills is not currently supported by the inventory discovery controller.
