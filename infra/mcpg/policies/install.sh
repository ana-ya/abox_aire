cat > infra/mcpg/install.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

UPSTREAM_REPO="https://github.com/techwithhuz/mcp-security-governance.git"
NAMESPACE="mcp-governance"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

git clone "$UPSTREAM_REPO" "$TMP_DIR"

kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f "$TMP_DIR/charts/mcp-governance/crds/"

docker build -t localhost/mcp-governance-controller:latest -f "$TMP_DIR/controller/Dockerfile" "$TMP_DIR/controller"
docker build -t localhost/mcp-governance-dashboard:latest -f "$TMP_DIR/dashboard/Dockerfile" "$TMP_DIR/dashboard"

kind load docker-image localhost/mcp-governance-controller:latest --name abox
kind load docker-image localhost/mcp-governance-dashboard:latest --name abox

helm upgrade --install mcp-governance "$TMP_DIR/charts/mcp-governance" \
  -n "$NAMESPACE"

kubectl apply -f infra/mcpg/policies/
EOF

chmod +x infra/mcpg/install.sh