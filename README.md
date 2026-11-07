# AegisShield — Zero-Trust Kubernetes with Helm, HPA and VPA

A portfolio-oriented, **not production-ready** Kubernetes reference project. It contains a 3-replica Nginx frontend and 3-replica Payment API design, PostgreSQL StatefulSet/PVC, TLS/authentication ingress definitions, and zero-trust NetworkPolicies. The Payment API image is a placeholder; no working payment service is bundled. Never process real card data with this example.

## Architecture

- **Tier 1**: ingress-nginx, TLS and external OIDC authentication proxy (external dependencies)
- **Tier 2**: Nginx frontend (HPA min 3, max 6)
- **Tier 3**: Payment API (HPA min 3, max 10)
- **Tier 4**: PostgreSQL StatefulSet with 10Gi PVC and database namespace isolation
- **Helm**: parameterized images, replica settings, storage, HPA and VPA
- **VPA**: `updateMode: Off` for all three workloads; recommendations only, avoids fighting HPA
<img width="1536" height="1024" alt="AegisShield Zero-Trust Kubernetes Architecture" src="https://github.com/user-attachments/assets/d34e9c40-7465-4939-b3fe-ed67974fa3d0" />

## Prerequisites

Kubernetes, Helm 3, a NetworkPolicy-enforcing CNI, Metrics Server (HPA), Vertical Pod Autoscaler CRDs/controller (VPA), suitable StorageClass, ingress-nginx controller, OIDC proxy, valid DNS and TLS secret, and a **real** Payment API container image. You must provision `postgres-credentials` in namespace `aegis-data` and the database credentials required by the API in namespace `aegis-app`; see `config/secrets-example.yaml`. Do not commit real credentials.

## Install

```bash
kubectl apply -f manifests/00-namespaces.yaml
# Install/verify Metrics Server and VPA from their maintained upstream projects first.
# Provision Secrets and TLS using a secret manager before installing the chart.
helm lint ./charts/aegisshield
helm template aegisshield ./charts/aegisshield -f ./charts/aegisshield/values-dev.yaml
helm upgrade --install aegisshield ./charts/aegisshield -n aegis-app -f ./charts/aegisshield/values-dev.yaml
kubectl -n aegis-app get deploy,hpa,vpa
kubectl -n aegis-data get sts,pvc,networkpolicy,vpa
kubectl -n aegis-app describe hpa payment-api
kubectl -n aegis-app describe vpa payment-api
```

`helm template` is for review; VPA manifests require VPA CRDs to be installed before a live Helm install. HPA requires Metrics Server and meaningful CPU load. The cluster must have enough schedulable capacity for additional replicas. The database NetworkPolicy allows inbound TCP/5432 only from labeled Payment API Pods in `aegis-app`. The app namespace is default-deny, with DNS and PostgreSQL egress exceptions; check ingress-controller labels and network-policy DNS behavior in your cluster.

## Verify autoscaling and isolation

1. Check `kubectl -n aegis-app get hpa -w` under controlled synthetic CPU load, and confirm scaling within configured bounds. Use a real API and load generator; the placeholder image cannot scale successfully.
2. Inspect `kubectl -n aegis-app describe vpa payment-api` for resource recommendations after sufficient observation time. VPA does not modify resources in `Off` mode.
3. Verify an allowed Payment API Pod can connect to PostgreSQL:5432, and a differently labeled Pod cannot. Verify disallowed egress and DNS behavior too.
4. Confirm unauthenticated ingress requests are rejected, TLS certificates are valid, and authenticated requests reach intended backends.
5. Run Helm upgrades/rollback and ensure HPA-managed replica counts are not overwritten by Helm.

## Security and production gaps

The example uses image tags rather than verified immutable digests, does not install a real Payment API, OIDC proxy, ingress controller, VPA, Metrics Server, external secret manager, backup system, or a production PostgreSQL operator. A one-replica PostgreSQL StatefulSet is **not highly available**. End-to-end PostgreSQL TLS, payment idempotency, provider tokenization, PCI DSS scoping, audit trails, encryption at rest, disaster recovery, policy admission, and threat-model review are required before real payments. NetworkPolicies alone are not authentication or encryption.

## File layout

- `charts/aegisshield/` — Helm chart, dev/prod values, HPA and VPA templates
- `manifests/00-namespaces.yaml` — namespace bootstrap
- `manifests/` — original static Kubernetes manifests (reference only; **do not apply in parallel** with Helm chart)
- `config/secrets-example.yaml` — example secret shape, not real secrets
