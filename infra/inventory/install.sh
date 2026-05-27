#!/usr/bin/env bash
set -euo pipefail

TMP_DIR="$(mktemp -d)"
git clone https://github.com/den-vasyliev/agentregistry-inventory.git "$TMP_DIR"

kubectl apply -f "$TMP_DIR/charts/agentregistry/crds/"

helm upgrade --install agentregistry-inventory "$TMP_DIR/charts/agentregistry" \
  -n agentregistry \
  --create-namespace

kubectl apply -f infra/inventory/discoveryconfig.yaml
kubectl apply -f infra/inventory/skillcatalogs/