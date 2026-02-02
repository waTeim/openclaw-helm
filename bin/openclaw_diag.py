#!/usr/bin/env python3
"""
openclaw_diag.py

Diagnostics for an OpenClaw StatefulSet using the Kubernetes Python client.
- No kubectl required
- Defaults namespace to current kubeconfig context namespace (or "default")
- Defaults statefulset name to "openclaw"

Usage examples:
  python openclaw_diag.py
  python openclaw_diag.py -n jeffw -s openclaw
  python openclaw_diag.py --print-token
  python openclaw_diag.py --tail-logs 200
"""

from __future__ import annotations

import argparse
import base64
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

from kubernetes import client, config
from kubernetes.client import ApiException


TOKEN_NAME_RE = re.compile(r"(GATEWAY|OPENCLAW|CLAWDBOT).*(TOKEN|AUTH)", re.IGNORECASE)


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def load_k8s_config() -> Tuple[str, str]:
    """
    Loads Kubernetes configuration.
    Returns (mode, context_namespace_default).
    mode is "kubeconfig" or "incluster".
    """
    # If running in cluster:
    try:
        config.load_incluster_config()
        return "incluster", os.environ.get("POD_NAMESPACE", "default")
    except Exception:
        pass

    # Fallback to local kubeconfig:
    config.load_kube_config()
    ns = "default"
    try:
        contexts, active = config.list_kube_config_contexts()
        if active:
            ns = (active.get("context", {}).get("namespace") or "default")
    except Exception:
        # Non-fatal; keep default
        pass
    return "kubeconfig", ns


def fmt_kv(title: str, items: Dict[str, str], indent: int = 2):
    pad = " " * indent
    print(f"{title}:")
    if not items:
        print(f"{pad}(none)")
        return
    for k, v in items.items():
        print(f"{pad}{k}: {v}")


def short_secret(value: str) -> str:
    if value is None:
        return "(none)"
    if len(value) <= 10:
        return value
    return f"{value[:4]}…{value[-4:]} (len={len(value)})"


def get_statefulset(apps: client.AppsV1Api, ns: str, name: str) -> client.V1StatefulSet:
    return apps.read_namespaced_stateful_set(name=name, namespace=ns)


def labels_to_selector(labels: Dict[str, str]) -> str:
    # e.g. {"app":"openclaw","release":"openclaw"} -> "app=openclaw,release=openclaw"
    return ",".join([f"{k}={v}" for k, v in (labels or {}).items()])


def pick_main_pod(pods: List[client.V1Pod], sts_name: str) -> Optional[client.V1Pod]:
    """
    Prefer pod named like "<sts_name>-0", else first running pod, else first pod.
    """
    if not pods:
        return None
    for p in pods:
        if p.metadata and p.metadata.name == f"{sts_name}-0":
            return p
    running = [p for p in pods if (p.status and p.status.phase == "Running")]
    if running:
        return running[0]
    return pods[0]


def find_container(pod: client.V1Pod, prefer: str = "gateway") -> Optional[client.V1Container]:
    if not pod.spec or not pod.spec.containers:
        return None
    for c in pod.spec.containers:
        if c.name == prefer:
            return c
    return pod.spec.containers[0]


def scan_env_for_token_candidates(container: client.V1Container) -> List[Tuple[str, str]]:
    """
    Returns list of (env_name, source_description).
    source_description can be 'value', 'secretKeyRef: secret/key', 'configMapKeyRef: ...'
    """
    hits = []
    if not container.env:
        return hits

    for env in container.env:
        name = env.name or ""
        if not TOKEN_NAME_RE.search(name):
            continue

        if env.value is not None:
            hits.append((name, f"value: {short_secret(env.value)}"))
        elif env.value_from:
            vf = env.value_from
            if vf.secret_key_ref:
                hits.append((name, f"secretKeyRef: {vf.secret_key_ref.name}/{vf.secret_key_ref.key}"))
            elif vf.config_map_key_ref:
                hits.append((name, f"configMapKeyRef: {vf.config_map_key_ref.name}/{vf.config_map_key_ref.key}"))
            else:
                hits.append((name, "valueFrom: (unknown)"))
        else:
            hits.append((name, "(empty)"))
    return hits


def collect_secret_refs(container: client.V1Container) -> List[Tuple[str, str, str]]:
    """
    Return list of (env_name, secret_name, secret_key) for env vars that are secretKeyRef.
    """
    out = []
    if not container.env:
        return out
    for env in container.env:
        if not env.value_from or not env.value_from.secret_key_ref:
            continue
        out.append((env.name, env.value_from.secret_key_ref.name, env.value_from.secret_key_ref.key))
    return out


def decode_secret_key(v1: client.CoreV1Api, ns: str, secret_name: str, key: str) -> Optional[str]:
    try:
        sec = v1.read_namespaced_secret(name=secret_name, namespace=ns)
    except ApiException as ex:
        eprint(f"  ! Failed reading secret {ns}/{secret_name}: {ex.status} {ex.reason}")
        return None

    data = (sec.data or {})
    if key not in data:
        eprint(f"  ! Secret {ns}/{secret_name} does not contain key '{key}' (has: {', '.join(data.keys())})")
        return None

    try:
        raw = base64.b64decode(data[key]).decode("utf-8", errors="replace")
        return raw.strip()
    except Exception as ex:
        eprint(f"  ! Failed decoding {ns}/{secret_name}[{key}]: {ex}")
        return None


def try_find_service(v1: client.CoreV1Api, ns: str, name: str) -> Optional[client.V1Service]:
    try:
        return v1.read_namespaced_service(name=name, namespace=ns)
    except ApiException:
        return None


def list_ingresses(networking: client.NetworkingV1Api, ns: str, name_hint: str) -> List[client.V1Ingress]:
    try:
        ing_list = networking.list_namespaced_ingress(namespace=ns)
    except ApiException:
        return []
    hits = []
    for ing in ing_list.items or []:
        if ing.metadata and (ing.metadata.name == name_hint or name_hint in ing.metadata.name):
            hits.append(ing)
    return hits


def tail_logs(v1: client.CoreV1Api, ns: str, pod: str, container: str, lines: int) -> str:
    return v1.read_namespaced_pod_log(
        name=pod,
        namespace=ns,
        container=container,
        tail_lines=lines,
        timestamps=True,
    )


def main():
    ap = argparse.ArgumentParser(description="OpenClaw Helm/K8s diagnostic (StatefulSet).")
    ap.add_argument("-n", "--namespace", default=None, help="Namespace (default: current kube context namespace)")
    ap.add_argument("-s", "--statefulset", default="openclaw", help='StatefulSet name (default: "openclaw")')
    ap.add_argument("--print-token", action="store_true", help="Decode and print candidate gateway token(s) from referenced Secrets (careful).")
    ap.add_argument("--tail-logs", type=int, default=0, help="If >0, tail this many log lines from main container.")
    args = ap.parse_args()

    mode, ctx_ns = load_k8s_config()
    ns = args.namespace or ctx_ns
    sts_name = args.statefulset

    print("== OpenClaw Diagnostic ==")
    print(f"Config mode: {mode}")
    print(f"Namespace:  {ns}")
    print(f"StatefulSet: {sts_name}")
    print("")

    v1 = client.CoreV1Api()
    apps = client.AppsV1Api()
    net = client.NetworkingV1Api()

    # 1) Fetch StatefulSet
    print("1) StatefulSet")
    try:
        sts = get_statefulset(apps, ns, sts_name)
        print(f"  ✓ Found StatefulSet {ns}/{sts_name}")
    except ApiException as ex:
        eprint(f"  ✗ Could not find StatefulSet {ns}/{sts_name}: {ex.status} {ex.reason}")
        sys.exit(2)

    replicas = sts.spec.replicas if sts.spec else None
    ready = sts.status.ready_replicas if sts.status else None
    print(f"  replicas: {replicas} | ready: {ready}")

    match_labels = (sts.spec.selector.match_labels if sts.spec and sts.spec.selector else {}) or {}
    selector = labels_to_selector(match_labels)
    fmt_kv("  selector labels", {k: v for k, v in match_labels.items()})
    print(f"  selector string: {selector or '(none)'}")
    print("")

    # 2) List pods for the StatefulSet
    print("2) Pods")
    try:
        pod_list = v1.list_namespaced_pod(namespace=ns, label_selector=selector if selector else None)
        pods = pod_list.items or []
    except ApiException as ex:
        eprint(f"  ✗ Failed listing pods in {ns}: {ex.status} {ex.reason}")
        sys.exit(2)

    if not pods:
        print("  ✗ No pods found for this StatefulSet selector.")
        sys.exit(2)

    for p in pods:
        name = p.metadata.name if p.metadata else "?"
        phase = p.status.phase if p.status else "?"
        pod_ip = p.status.pod_ip if p.status else "?"
        print(f"  - {name:30} {phase:10} ip={pod_ip}")
    pod = pick_main_pod(pods, sts_name)
    if not pod or not pod.metadata:
        print("  ✗ Could not select a pod to inspect.")
        sys.exit(2)

    pod_name = pod.metadata.name
    print(f"  -> Inspecting pod: {pod_name}")
    print("")

    # 3) Inspect container + env
    print("3) Container / Env / Token candidates")
    container = find_container(pod, prefer="gateway")
    if not container:
        print("  ✗ No containers found on pod.")
        sys.exit(2)

    print(f"  container: {container.name}")
    print(f"  image:     {container.image}")

    env_hits = scan_env_for_token_candidates(container)
    if env_hits:
        print("  token-related env vars found:")
        for name, src in env_hits:
            print(f"    - {name}: {src}")
    else:
        print("  (no token-related env vars matched pattern)")

    # envFrom sources (often used for Secrets/ConfigMaps)
    if container.env_from:
        print("  envFrom sources:")
        for ef in container.env_from:
            if ef.secret_ref:
                print(f"    - secretRef: {ef.secret_ref.name}")
            if ef.config_map_ref:
                print(f"    - configMapRef: {ef.config_map_ref.name}")
    print("")

    # 4) Decode secrets if requested
    if args.print_token:
        print("4) Secret decoding (requested)")
        refs = collect_secret_refs(container)

        # Also scan envFrom secretRef keys if possible (we can't know which key is token without inspecting)
        envfrom_secrets = []
        if container.env_from:
            for ef in container.env_from:
                if ef.secret_ref and ef.secret_ref.name:
                    envfrom_secrets.append(ef.secret_ref.name)

        decoded_any = False

        if refs:
            print("  secretKeyRef env vars:")
            for env_name, sec_name, sec_key in refs:
                if TOKEN_NAME_RE.search(env_name) or TOKEN_NAME_RE.search(sec_key):
                    val = decode_secret_key(v1, ns, sec_name, sec_key)
                    if val is not None:
                        decoded_any = True
                        print(f"    - {env_name} from {sec_name}/{sec_key}: {val}")
        else:
            print("  (no secretKeyRef env vars found)")

        if envfrom_secrets:
            print("  envFrom secretRefs (scanning for likely token keys):")
            for sec_name in envfrom_secrets:
                try:
                    sec = v1.read_namespaced_secret(sec_name, ns)
                except ApiException as ex:
                    eprint(f"    ! Failed reading secret {ns}/{sec_name}: {ex.status} {ex.reason}")
                    continue
                keys = list((sec.data or {}).keys())
                likely = [k for k in keys if TOKEN_NAME_RE.search(k)]
                print(f"    - {sec_name}: keys={keys}")
                if likely:
                    print(f"      likely token keys: {likely}")
                    for k in likely:
                        val = decode_secret_key(v1, ns, sec_name, k)
                        if val is not None:
                            decoded_any = True
                            print(f"      {sec_name}/{k}: {val}")

        if not decoded_any:
            print("  (no token decoded; either none present or key naming didn't match)")
        print("")
    else:
        print("4) Secret decoding")
        print("  (skipped; re-run with --print-token to decode token values from referenced Secrets)")
        print("")

    # 5) Service/Ingress presence
    print("5) Service / Ingress")
    svc = try_find_service(v1, ns, sts_name)
    if svc:
        t = svc.spec.type if svc.spec else "?"
        ports = []
        if svc.spec and svc.spec.ports:
            for p in svc.spec.ports:
                ports.append(f"{p.port}/{p.protocol}")
        print(f"  ✓ Service {ns}/{sts_name}: type={t} ports={ports or '(none)'}")
        if svc.spec and svc.spec.cluster_ip:
            print(f"    clusterIP={svc.spec.cluster_ip}")
    else:
        print(f"  (no Service named {ns}/{sts_name})")

    ing_hits = list_ingresses(net, ns, sts_name)
    if ing_hits:
        print(f"  ✓ Ingresses matching '{sts_name}':")
        for ing in ing_hits:
            n = ing.metadata.name if ing.metadata else "?"
            hosts = []
            if ing.spec and ing.spec.rules:
                for r in ing.spec.rules:
                    if r.host:
                        hosts.append(r.host)
            print(f"    - {n} hosts={hosts or '(none)'}")
    else:
        print("  (no matching Ingress found)")
    print("")

    # 6) Quick pod conditions/events
    print("6) Pod status summary")
    phase = pod.status.phase if pod.status else "?"
    print(f"  phase: {phase}")
    if pod.status and pod.status.conditions:
        for c in pod.status.conditions:
            print(f"  condition {c.type:18} = {c.status} (reason={c.reason or ''})")
    print("")

    # 7) Optional log tail
    if args.tail_logs and args.tail_logs > 0:
        print("7) Log tail")
        try:
            text = tail_logs(v1, ns, pod_name, container.name, args.tail_logs)
            print(text.rstrip())
        except ApiException as ex:
            eprint(f"  ✗ Failed to read logs: {ex.status} {ex.reason}")
        print("")
    else:
        print("7) Log tail")
        print("  (skipped; re-run with --tail-logs N to fetch logs)")
        print("")

    print("== Done ==")
    print("Tip: If the dashboard says 'gateway token missing', re-run with --print-token and look for a token env/secret.")
    print("     If you're using NetworkPolicy with default-deny egress, ensure egress to the API server is allowed.")


if __name__ == "__main__":
    main()
