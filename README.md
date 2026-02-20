# OpenClaw Kube

Kubernetes resources for deploying [OpenClaw](https://github.com/openclaw/openclaw) - a personal AI assistant with multi-channel support (WhatsApp, Telegram, Discord).

## Repository Structure

| Path | Description |
|------|-------------|
| [chart/](./chart/) | Helm chart for deploying OpenClaw on Kubernetes |
| [Dockerfile](./Dockerfile) | Builds OpenClaw + Playwright addon image |
| [Makefile](./Makefile) | Image build/push targets (reads `build-config.json`) |
| [bin/](./bin/) | Operational scripts (`configure.py`, `openclaw_diag.py`) |
| [prompts/](./prompts/) | Historical build prompts used during chart development |

## Quick Start

```bash
# Clone the repository
git clone https://github.com/openclaw/openclaw-kube.git
cd openclaw-kube

# Install with default values
helm install openclaw ./chart

# Access via port-forward
kubectl port-forward openclaw-0 18789:18789

# Visit http://localhost:18789
```

## Image Build

### Update to Latest OpenClaw Release

```bash
# Updates chart/values.yaml image.tag to the latest OpenClaw release
make update-tag
```

The `Dockerfile` extends an upstream OpenClaw base image with Playwright browsers. Use `bin/configure.py` to set the source and target image coordinates, then build with Make.

```bash
# Configure (interactive — answers saved to build-config.json for next time)
make configure

# Build the image
make build

# Build and push
make push
```

You can also pass values directly:

```bash
python3 bin/configure.py \
  --source-registry ghcr.io --source-image openclaw/openclaw --source-tag latest \
  --target-registry ghcr.io/myorg --target-image openclaw-playwright
```

## Usage

### Basic Installation

```bash
helm install openclaw ./chart
```

### With Ingress and TLS

```bash
helm install openclaw ./chart \
  --set ingress.enabled=true \
  --set ingress.domain=openclaw.example.com \
  --set ingress.tls.enabled=true \
  --set ingress.tls.certManager.enabled=true
```

### Using Example Values

```bash
# Minimal (local development)
helm install openclaw ./chart -f chart/examples/values-minimal.yaml

# Production with ingress
helm install openclaw ./chart -f chart/examples/values-ingress.yaml

# With RBAC for sandbox execution
helm install openclaw ./chart -f chart/examples/values-rbac-operator.yaml

# Automatic non-interactive onboarding
helm install openclaw ./chart -f chart/examples/values-noninteractive-onboard.yaml
```

### Production Secrets

For production, create secrets externally rather than in values:

```bash
# Create secret
kubectl create secret generic openclaw-secrets \
  --from-literal=gatewayToken=$(openssl rand -hex 32) \
  --from-literal=anthropicApiKey=sk-ant-your-key \
  --from-literal=claudeSessionKey=your-session-key

# Install referencing the secret
helm install openclaw ./chart \
  --set secrets.create=false \
  --set secrets.existingSecret=openclaw-secrets
```

## Configuration

Key configuration options:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Must be 1 (single-user architecture) | `1` |
| `image.repository` | Container image | `openclaw/openclaw` |
| `gateway.port` | Gateway HTTP port | `18789` |
| `persistence.enabled` | Enable persistent storage | `true` |
| `persistence.size` | Storage size | `10Gi` |
| `ingress.enabled` | Enable ingress | `false` |
| `ingress.domain` | Ingress domain | `""` |
| `secrets.existingSecret` | Use external secret | `""` |
| `rbac.create` | Create namespaced RBAC | `false` |
| `onboarding.enabled` | Auto-onboarding initContainer | `false` |

See [chart/values.yaml](./chart/values.yaml) for full configuration reference.

## Architecture

OpenClaw is a **single-user, stateful application**. The chart deploys:

- **StatefulSet** with 1 replica (scaling not supported)
- **Persistent Volume** for configuration, sessions, and workspace
- **Service** on port 18789 (gateway) and optionally 18790 (bridge)
- **Ingress** (optional) with TLS support

## Post-Installation

### Get Gateway Token

```bash
kubectl get secret openclaw -o jsonpath='{.data.gatewayToken}' | base64 -d
```

### Configure Channels

```bash
# Discord
kubectl exec -it openclaw-0 -- node dist/index.js channels add --channel discord --token YOUR_TOKEN

# Telegram
kubectl exec -it openclaw-0 -- node dist/index.js channels add --channel telegram --token YOUR_TOKEN

# WhatsApp (interactive)
kubectl exec -it openclaw-0 -- node dist/index.js channels login
```

### Health Check

```bash
kubectl exec -it openclaw-0 -- node dist/index.js health
```

## Sources

This project builds upon:

- **[OpenClaw](https://github.com/openclaw/openclaw)** - The upstream OpenClaw project providing the AI assistant functionality, container images, and deployment documentation
- **[sirily11/clawdbot](https://github.com/sirily11/clawdbot)** - Original Clawdbot Helm chart by [@sirily11](https://github.com/sirily11), providing Kubernetes deployment patterns, persistence, probes, and security configuration

## Development

### Prerequisites

- Kubernetes 1.19+
- Helm 3.x
- kubectl

### Linting

```bash
helm lint ./chart
```

### Template Rendering

```bash
helm template openclaw ./chart
helm template openclaw ./chart --debug
```

### Dry-Run Installation

```bash
helm install openclaw ./chart --dry-run --debug
```

### Testing

```bash
helm install openclaw ./chart
helm test openclaw
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and test with `helm lint` and `helm template`
4. Submit a pull request

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details.
