# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Kubernetes Helm chart repository containing:
- **clawdbot/** - Main Helm chart for deploying Clawdbot, a single-user personal AI assistant with multi-channel support (WhatsApp, Telegram, Discord)
- **openclaw/** - Generic Helm chart template for standard Kubernetes deployments

## Common Commands

```bash
# Lint charts
helm lint ./clawdbot
helm lint ./openclaw

# Template rendering (debug)
helm template clawdbot ./clawdbot
helm template clawdbot ./clawdbot -f clawdbot/examples/values-production.yaml

# Dry-run installation
helm install test ./clawdbot --dry-run --debug

# Package for release
helm package ./clawdbot -d .cr-release-packages
helm repo index .cr-release-packages --url https://clawdbot.github.io/clawdbot

# Validate schema
helm lint ./clawdbot --strict
```

## Architecture

### Clawdbot Chart

Uses **StatefulSet** (not Deployment) for persistent state management:
- **Single-user architecture**: `replicaCount` must always be 1 (enforced by schema)
- **Persistent volumes** with two subPaths:
  - `/home/node/.clawdbot` (subPath: `clawdbot-state`) - Configuration, sessions, SQLite databases
  - `/home/node/clawd` (subPath: `clawdbot-workspace`) - Agent workspace
- **Gateway service** on port 18789 with configurable bind modes (loopback, lan, auto)

Key templates:
- `statefulset.yaml` - Main workload with health probes and volume mounts
- `configmap.yaml` - Generates `clawdbot.json` configuration
- `secret.yaml` - API keys (Anthropic, OpenAI) and channel tokens

Security context runs as non-root (uid/gid: 1000) with minimal capabilities.

### OpenClaw Chart

Standard Deployment-based chart with HPA support, suitable as a starting template for generic applications.

## Configuration

Example values files in `clawdbot/examples/`:
- `values-basic.yaml` - Local development (5Gi storage, no ingress)
- `values-production.yaml` - Production deployment (20Gi, nginx ingress, cert-manager)
- `values-fly-like.yaml` - Fly.io-optimized configuration

Schema validation in `clawdbot/values.schema.json` enforces:
- replicaCount: exactly 1
- Storage size pattern: `^[0-9]+(Gi|Mi|Ti)$`
- Valid gateway ports and bind modes

## Development Environment

The `.devcontainer/` provides a fully configured VS Code Dev Container with:
- kubectl, helm, kubelogin pre-installed with bash completion
- Go 1.24, Node.js LTS, Python 3.12
- Claude Code and MCP tools (post-create)

Mount points for credentials are configured at `~/.vscode-projects/[project]/`.
