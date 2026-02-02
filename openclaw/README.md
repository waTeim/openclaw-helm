# OpenClaw Helm Chart

A Helm chart for deploying [OpenClaw](https://openclaw.bot) - a personal AI assistant with multi-channel support (WhatsApp, Telegram, Discord).

## TL;DR

```bash
helm install openclaw ./openclaw
kubectl port-forward openclaw-0 18789:18789
# Visit http://localhost:18789
```

## Prerequisites

- Kubernetes 1.19+
- Helm 3.x
- PV provisioner support (for persistence)

## Architecture

OpenClaw is a **single-user, stateful application**. This chart deploys a StatefulSet with:

- `replicaCount: 1` (required - scaling is not supported)
- Persistent storage for configuration, sessions, and workspace
- Gateway service on port 18789 (HTTP API/WebUI)
- Optional bridge service on port 18790 (IPC)

## Installation

### Basic Installation

```bash
helm install openclaw ./openclaw
```

### With Custom Values

```bash
helm install openclaw ./openclaw -f my-values.yaml
```

### Example Configurations

```bash
# Minimal (local development)
helm install openclaw ./openclaw -f examples/values-minimal.yaml

# With Ingress and TLS
helm install openclaw ./openclaw -f examples/values-ingress.yaml

# With RBAC for sandbox execution
helm install openclaw ./openclaw -f examples/values-rbac-operator.yaml

# With automatic onboarding
helm install openclaw ./openclaw -f examples/values-noninteractive-onboard.yaml
```

## Configuration

### Key Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Must be 1 (single-user architecture) | `1` |
| `image.registry` | Container registry | `ghcr.io` |
| `image.repository` | Image repository | `openclaw/openclaw` |
| `image.tag` | Image tag | Chart appVersion |
| `gateway.bind` | Binding mode (loopback/lan/auto) | `lan` |
| `gateway.port` | Gateway HTTP port | `18789` |
| `gateway.bridgePort` | Bridge IPC port | `18790` |
| `persistence.enabled` | Enable persistent storage | `true` |
| `persistence.size` | PVC size | `10Gi` |
| `ingress.enabled` | Enable ingress | `false` |
| `ingress.domain` | Ingress domain | `""` |
| `secrets.create` | Create secret from values | `true` |
| `secrets.existingSecret` | Use existing secret | `""` |
| `rbac.create` | Create namespaced RBAC | `false` |
| `onboarding.enabled` | Auto-onboarding via initContainer | `false` |

### Secrets Management

**Development/Testing** (not recommended for production):

```yaml
secrets:
  create: true
  data:
    gatewayToken: ""  # Auto-generated
    claudeSessionKey: "your-session-key"
    anthropicApiKey: "sk-ant-..."
```

**Production** (recommended):

```bash
# Create secret manually
kubectl create secret generic openclaw-secrets \
  --from-literal=gatewayToken=$(openssl rand -hex 32) \
  --from-literal=claudeSessionKey=YOUR_SESSION_KEY \
  --from-literal=anthropicApiKey=YOUR_API_KEY

# Reference in values
secrets:
  create: false
  existingSecret: openclaw-secrets
```

### Onboarding Modes

OpenClaw requires initial setup. Three options:

1. **Manual onboarding** (default): Exec into pod and run interactively
   ```bash
   kubectl exec -it openclaw-0 -- node dist/index.js onboard
   ```

2. **Automatic onboarding**: Enable initContainer for non-interactive setup
   ```yaml
   onboarding:
     enabled: true
   ```

3. **Pre-configured**: Mount existing state/config (skip onboarding entirely)
   ```yaml
   onboarding:
     enabled: false
   config:
     existingConfigMap: my-openclaw-config
   ```

### Persistence

Storage paths:
- `/home/node/.openclaw` - Configuration, credentials, sessions (subPath: `openclaw-state`)
- `/home/node/.openclaw/workspace` - Agent workspace (subPath: `openclaw-workspace`)

```yaml
persistence:
  enabled: true
  size: 10Gi
  storageClass: ""  # Use cluster default
  accessMode: ReadWriteOnce
```

**Warning**: Disabling persistence will lose all state on pod restart.

### Ingress

```yaml
ingress:
  enabled: true
  className: nginx
  domain: openclaw.example.com
  tls:
    enabled: true
    certManager:
      enabled: true
      issuer: letsencrypt-prod
  annotations:
    # WebSocket support
    nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"
```

### RBAC

By default, no RBAC is created (least privilege). Enable RBAC only if OpenClaw needs to create pods/jobs for sandbox execution:

```yaml
rbac:
  create: true
  rules:
    - apiGroups: [""]
      resources: ["pods", "pods/log"]
      verbs: ["get", "list", "watch", "create", "delete"]
    - apiGroups: ["batch"]
      resources: ["jobs"]
      verbs: ["get", "list", "watch", "create", "delete"]

serviceAccount:
  automount: true  # Required for RBAC to work
```

**Note**: This creates a namespaced Role (not ClusterRole), limiting permissions to the release namespace only.

## Security

Default security configuration:

```yaml
podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  seccompProfile:
    type: RuntimeDefault

securityContext:
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
  readOnlyRootFilesystem: false  # Node.js needs /tmp
```

This configuration is compatible with PodSecurity "restricted" policy.

## Health Checks

| Probe | Type | Purpose |
|-------|------|---------|
| Startup | TCP 18789 | Allow initial startup (up to 150s) |
| Readiness | TCP 18789 | Ready to receive traffic |
| Liveness | Exec `health` | Deep health check |

## Upgrading

```bash
helm upgrade openclaw ./openclaw -f my-values.yaml
```

The StatefulSet will perform a rolling update. State is preserved in the PVC.

## Troubleshooting

### Check pod status

```bash
kubectl get statefulset openclaw
kubectl describe pod openclaw-0
```

### View logs

```bash
# Main container
kubectl logs -f openclaw-0

# Init containers (if enabled)
kubectl logs openclaw-0 -c init-config
kubectl logs openclaw-0 -c onboarding
```

### Get gateway token

```bash
kubectl get secret openclaw -o jsonpath='{.data.gatewayToken}' | base64 -d
```

### Manual health check

```bash
kubectl exec -it openclaw-0 -- node dist/index.js health
```

### Run diagnostics

```bash
kubectl exec -it openclaw-0 -- node dist/index.js doctor
```

## Verification

```bash
# Lint chart
helm lint ./openclaw

# Render templates
helm template openclaw ./openclaw

# Dry-run install
helm install openclaw ./openclaw --dry-run --debug

# Run tests after install
helm test openclaw
```

## Uninstalling

```bash
helm uninstall openclaw
```

**Note**: PVCs are not deleted automatically. To remove all data:

```bash
kubectl delete pvc data-openclaw-0
```
