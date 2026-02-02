## Improved Prompt: Build a Production-Grade OpenClaw Helm Chart

You are working in a repo that contains three relevant directories:

- `clawdbot/` — an older Helm chart built when the project was called “clawdbot”. This chart includes useful patterns for Kubernetes deployment (persistence, probes, securityContext, ingress, secrets/config handling). It may be behind the upstream OpenClaw project.
- `openclaw/` — a new chart skeleton created via `helm create openclaw`. This is the chart you must implement and make correct.
- `upstream/` — a checkout (or snapshot) of the upstream OpenClaw project. This contains:
  - container build source (Dockerfile / image expectations)
  - `docker-compose` deployment definitions
  - install docs under `upstream/doc/install` describing required env vars, config files, onboarding flow, ports, and runtime behavior.

### Objective

Modify the chart in `openclaw/` so that it deploys OpenClaw correctly and robustly on Kubernetes, using the upstream OpenClaw image and deployment model (not the legacy clawdbot naming), while incorporating good ideas from the `clawdbot/` chart where applicable.

The resulting chart must be suitable for a “home cluster” but designed with production-grade defaults: safe, least privilege, persistent state, and clear configuration points.

### Hard Requirements (must satisfy)

1. **Single-replica architecture**
   - Default `replicaCount: 1`.
   - Document why (stateful single-user architecture).
   - If you support scaling >1, it must be explicitly “unsupported” or gated with strong warnings and a different persistence strategy.

2. **Persistence**
   - Provide a PVC for OpenClaw state directory and workspace directory.
   - Use defaults compatible with common storage classes (e.g., Longhorn, local-path, etc.).
   - Allow disabling persistence for dev/test but warn that it breaks onboarding persistence.

3. **Configuration & Secrets**
   - Support both patterns:
     - inline config via ConfigMap (`config.create: true` + `config.data`)
     - referencing an existing ConfigMap (`config.existingConfigMap`)
   - Support secrets similarly:
     - `secrets.create: true` (dev/test only)
     - `secrets.existingSecret` (recommended)
   - Never require users to commit API keys to Git. Document best practice clearly.
   - Ensure the container can read env vars for API keys and gateway token as described in upstream docs.

4. **Onboarding / Setup**
   - OpenClaw has an interactive setup in some docs, but it also supports a scriptable onboarding path.
   - Implement Kubernetes-friendly onboarding:
     - Provide a values option to run `openclaw onboard --non-interactive` automatically via **initContainer** or **post-install Job hook** (choose the best option and justify).
     - Make it idempotent: onboarding should not overwrite existing state on restart/upgrade.
     - Allow opting out entirely when user mounts config/state already.
   - Ensure the main container can start without TTY interaction.

5. **Networking**
   - Expose the gateway port as a Service.
   - Ingress optional; include websocket-friendly defaults (or document).
   - Provide a safe default bind strategy (prefer loopback/cluster-internal unless user opts into LAN bind/ingress).
   - Allow `gateway.port` override.

6. **Security**
   - Provide secure defaults:
     - `runAsNonRoot`, drop Linux capabilities, `allowPrivilegeEscalation: false`, `seccompProfile: RuntimeDefault`.
     - Avoid privileged and host mounts.
   - ServiceAccount creation must be optional and default to `true`.
   - RBAC:
     - Default: no extra RBAC (least privilege).
     - Optional: enable a namespaced Role + RoleBinding granting permission to create pods/jobs/etc **only in the release namespace** (no ClusterRoleBinding). Make this opt-in with values like `rbac.create: true` and a clearly documented ruleset.
   - Provide Pod annotations hooks and support PodSecurity “restricted” compatibility.

7. **Probes & lifecycle**
   - Implement startup/readiness/liveness probes based on upstream behavior and/or clawdbot chart patterns.
   - Add lifecycle preStop cleanup if upstream needs lock removal (carry over if still relevant).

8. **Compatibility**
   - Chart must work on common clusters (k3s, kubeadm, Talos) with standard Kubernetes APIs.
   - Avoid vendor-specific CRDs unless optional and gated (cert-manager integration optional).

### Implementation Guidance

- Treat `upstream/doc/install` and `upstream/docker-compose.*` as source of truth for:
  - required env vars
  - required filesystem paths
  - expected ports
  - startup command/entrypoint
  - onboarding flags and non-interactive mode
- Use `clawdbot/` chart as a reference for patterns and ergonomics (values structure, persistence layout, probes, ingress annotations), but **rename everything and align it to OpenClaw**:
  - image repo should default to the upstream OpenClaw image
  - config paths and env vars should match upstream
  - naming should be `openclaw`, not `clawdbot`

### Deliverables

1. A fully implemented Helm chart in `openclaw/` including:
   - templates: deployment/statefulset (choose and justify), service, ingress, pvc, configmap, secret, serviceaccount, role/rolebinding (optional), tests
   - values.yaml with comments
   - values.schema.json if useful
   - README.md that documents install, upgrade, onboarding modes, and security options

2. A small set of example values files under `openclaw/examples/`:
   - `values-minimal.yaml` (cluster-internal, port-forward use)
   - `values-ingress.yaml` (ingress enabled, TLS optional)
   - `values-rbac-operator.yaml` (namespaced RBAC enabled for pod/job creation)
   - `values-noninteractive-onboard.yaml` (init/job onboarding enabled)

3. Tests and verification steps:
   - Helm template validation (`helm lint`, `helm template`)
   - Chart-testing suggestions if feasible
   - A “smoke test” manifest/steps: install into a throwaway namespace, wait for readiness, port-forward and hit health endpoint or tcp check
   - Explicit checks: no ClusterRoleBinding, persistence mounted correctly, onboarding idempotent

### Decision Policy (avoid unnecessary questions)

If something is unclear, do the following in order:

1. Search in `upstream/` for the relevant truth (commands, env vars, config filenames).
2. If still unclear, infer from docker-compose behavior.
3. If still unclear, adopt a safe default that:
   - keeps gateway internal (ClusterIP, loopback bind if applicable)
   - uses least privilege
   - does not expose secrets in values
   - does not enable RBAC or ingress by default
4. Only ask a clarifying question if you are blocked and cannot proceed safely.

### Concrete Tasks (do these explicitly)

1. Read and summarize (briefly in your own notes) what upstream expects:
   - default port(s)
   - required env vars
   - state/workspace paths
   - startup command
   - onboarding flags (especially non-interactive)
2. Implement chart templates accordingly.
3. Add idempotent onboarding:
   - check for a marker file in the state dir, or check existence of config/auth profile file before running
4. Add optional namespaced RBAC block.
5. Run `helm lint openclaw` and render templates. Fix warnings/errors.
6. Provide a final summary of what changed and how to install.

### Optional Enhancements (nice to have if time permits)

- Support extraContainers and initContainers via values.
- Support NetworkPolicy templates (default deny + allow DNS + allow API server) gated by `networkPolicy.enabled`.
- Support PodDisruptionBudget for graceful upgrades (even if replica=1).
- Support topologySpreadConstraints/affinity defaults.
