#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="qdrant"

helm repo add qdrant https://qdrant.github.io/qdrant-helm || true
helm repo update

kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

helm upgrade --install qdrant qdrant/qdrant \
  -n "$NAMESPACE" \
  -f infra/qdrant/values.yaml