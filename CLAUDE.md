# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Kubernetes repository (`openclaw-kube`) for deploying [OpenClaw](https://github.com/openclaw/openclaw) - a single-user personal AI assistant with multi-channel support (WhatsApp, Telegram, Discord).

### Repository Structure

- **chart/** - Helm chart for deploying OpenClaw on Kubernetes
- **bin/** - Operational scripts (`configure.py`, `openclaw_diag.py`)
- **Dockerfile** - Builds an OpenClaw + Playwright addon image from an upstream base
- **Makefile** - Image build/push targets, reads config from `build-config.json`
- **prompts/v1/** - Historical build prompts used during initial chart development

## Common Commands

```bash
# Configure image build (interactive, saves to build-config.json)
make configure          # or: python3 bin/configure.py

# Build and push container image
make build
make push

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

## Image Build

The `Dockerfile` extends an upstream OpenClaw base image with Playwright browser
support. `bin/configure.py` prompts for source and target image coordinates
(registry, image, tag) and writes `build-config.json`. The `Makefile` reads
this JSON directly via `$(shell python3 ...)` — no intermediate `make.env`.

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
