# OpenClaw Helm Chart

Helm chart for deploying [OpenClaw](https://github.com/openclaw/openclaw) - a personal AI assistant with multi-channel support (WhatsApp, Telegram, Discord) - on Kubernetes.

## Charts

| Chart | Description | Version |
|-------|-------------|---------|
| [openclaw](./openclaw/) | Production-grade Helm chart for OpenClaw | 1.2.0 |
| [clawdbot](./clawdbot/) | Legacy chart (for reference, use openclaw) | 1.0.0 |

## Quick Start

```bash
# Add the repository (if published)
# helm repo add openclaw https://openclaw.github.io/openclaw-helm
# helm repo update

# Or install from local checkout
git clone https://github.com/openclaw/openclaw-helm.git
cd openclaw-helm

# Install with default values
helm install openclaw ./openclaw

# Access via port-forward
kubectl port-forward openclaw-0 18789:18789

# Visit http://localhost:18789
```

## Usage

### Basic Installation

```bash
helm install openclaw ./openclaw
```

### With Ingress and TLS

```bash
helm install openclaw ./openclaw \
  --set ingress.enabled=true \
  --set ingress.domain=openclaw.example.com \
  --set ingress.tls.enabled=true \
  --set ingress.tls.certManager.enabled=true
```

### Using Example Values

```bash
# Minimal (local development)
helm install openclaw ./openclaw -f openclaw/examples/values-minimal.yaml

# Production with ingress
helm install openclaw ./openclaw -f openclaw/examples/values-ingress.yaml

# With RBAC for sandbox execution
helm install openclaw ./openclaw -f openclaw/examples/values-rbac-operator.yaml

# Automatic non-interactive onboarding
helm install openclaw ./openclaw -f openclaw/examples/values-noninteractive-onboard.yaml
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
helm install openclaw ./openclaw \
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

See [openclaw/values.yaml](./openclaw/values.yaml) for full configuration reference.

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
helm lint ./openclaw
helm lint ./clawdbot
```

### Template Rendering

```bash
helm template openclaw ./openclaw
helm template openclaw ./openclaw --debug
```

### Dry-Run Installation

```bash
helm install openclaw ./openclaw --dry-run --debug
```

### Testing

```bash
helm install openclaw ./openclaw
helm test openclaw
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and test with `helm lint` and `helm template`
4. Submit a pull request

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details.
