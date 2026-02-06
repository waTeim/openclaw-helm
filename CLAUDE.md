# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Kubernetes repository (`openclaw-kube`) for deploying [OpenClaw](https://github.com/openclaw/openclaw) - a single-user personal AI assistant with multi-channel support (WhatsApp, Telegram, Discord).

### Repository Structure

- **chart/** - Helm chart for deploying OpenClaw on Kubernetes
- **bin/** - Diagnostic and operational scripts (e.g., `openclaw_diag.py`)
- **prompts/v1/** - Historical build prompts used during initial chart development

## Common Commands

```bash
# Lint chart
helm lint ./chart

# Template rendering (debug)
helm template openclaw ./chart
helm template openclaw ./chart -f chart/examples/values-minimal.yaml

# Dry-run installation
helm install test ./chart --dry-run --debug

# Package for release
helm package ./chart -d .cr-release-packages

# Validate schema
helm lint ./chart --strict
```

## Architecture

### OpenClaw Chart (`chart/`)

Uses **StatefulSet** (not Deployment) for persistent state management:
- **Single-user architecture**: `replicaCount` must always be 1 (enforced by schema)
- **Persistent volumes** with two subPaths:
  - `/home/node/.openclaw` (subPath: `openclaw-state`) - Configuration, credentials, sessions
  - `/home/node/.openclaw/workspace` (subPath: `openclaw-workspace`) - Agent workspace
- **Gateway service** on port 18789 with configurable bind modes (loopback, lan, auto)

Key templates:
- `statefulset.yaml` - Main workload with health probes and volume mounts
- `configmap.yaml` - Generates `openclaw.json` configuration
- `secret.yaml` - API keys (Anthropic, OpenAI) and channel tokens

Security context runs as non-root (uid/gid: 1000) with minimal capabilities.

## Configuration

Example values files in `chart/examples/`:
- `values-minimal.yaml` - Local development (port-forward, no ingress)
- `values-ingress.yaml` - Ingress with optional TLS / cert-manager
- `values-rbac-operator.yaml` - Namespaced RBAC for sandbox pod/job creation
- `values-noninteractive-onboard.yaml` - Automatic non-interactive onboarding via initContainer

Schema validation in `chart/values.schema.json` enforces:
- replicaCount: exactly 1
- Storage size pattern: `^[0-9]+(Gi|Mi|Ti)$`
- Valid gateway ports and bind modes

## Development Environment

The `.devcontainer/` provides a fully configured VS Code Dev Container with:
- kubectl, helm pre-installed
- Go 1.24, Node.js LTS, Python 3.12
- Claude Code (post-create)

Mount points for credentials are configured at `~/.vscode-projects/[project]/`.
