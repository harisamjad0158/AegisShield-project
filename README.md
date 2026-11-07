# AegisShield — Zero-Trust Kubernetes with Helm, HPA and VPA

AegisShield is a cloud-native DevSecOps demonstration platform that runs a simulated payment application on Kubernetes.

The project integrates NGINX, FastAPI, PostgreSQL, Helm, Kubernetes NetworkPolicies, Keycloak, OAuth2 Proxy, HPA, and VPA.

Users can create simulated payments through a web dashboard and retrieve stored transactions by UUID.

**Disclaimer:** This is a portfolio and development project, not a production-ready payment processing system. No real payments or card data are processed.

## Architecture

![AegisShield Zero-Trust Kubernetes Architecture](https://github.com/user-attachments/assets/d34e9c40-7465-4939-b3fe-ed67974fa3d0)

```text
Browser
  |
  | localhost:8082
  v
NGINX Frontend (3 replicas)
  |
  | /api/
  v
FastAPI Payment API (3 replicas)
  |
  | TCP 5432
  v
PostgreSQL StatefulSet
  |
  v
PersistentVolumeClaim (10Gi)
```

The project also includes authenticated ingress through Keycloak and OAuth2 Proxy, default-deny NetworkPolicies, and horizontal and vertical autoscaling configurations.

## Stage 1 — Prepare Ubuntu

Update Ubuntu:

```bash
sudo apt update
sudo apt upgrade -y
```

Install basic tools:

```bash
sudo apt install -y \
  curl \
  wget \
  git \
  jq \
  ca-certificates \
  gnupg \
  python3 \
  python3-pip \
  openssl
```

Verify:

```bash
git --version
python3 --version
curl --version
```

### Install Docker

Follow the official Docker installation instructions for your Ubuntu version:

https://docs.docker.com/engine/install/ubuntu/

After installation:

```bash
sudo systemctl enable --now docker

docker version
docker info
```

## Stage 2 — Install Kubernetes Tools

Install kubectl:

https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/

Install KinD:

https://kind.sigs.k8s.io/docs/user/quick-start/

Install Helm:

https://helm.sh/docs/intro/install/

Verify:

```bash
kubectl version --client

kind version

helm version

docker version
```

## Stage 3 — Clone AegisShield

Clone the repository:

```bash
cd ~/Downloads

git clone https://github.com/harisamjad0158/AegisShield-project.git

cd AegisShield-project
```

Review the repository:

```bash
pwd

git status

find . -maxdepth 3 -type f | sort
```

**Important:** The GitHub repository name and the original Ubuntu working-directory name differ. All subsequent commands assume you are inside the cloned repository root.

## Stage 4 — Create the Kubernetes Cluster

AegisShield was developed using a local KinD cluster named `aegisshield-cluster`.

Check existing clusters:

```bash
kind get clusters
```

For a basic development cluster, create a multi-node KinD cluster:

```bash
cat > /tmp/aegisshield-kind.yaml <<'KIND'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
  - role: worker
KIND

kind create cluster \
  --name aegisshield-cluster \
  --config /tmp/aegisshield-kind.yaml
```

Select the context:

```bash
kubectl config use-context kind-aegisshield-cluster

kubectl get nodes -o wide

kubectl cluster-info
```

**Important:** This is a basic cluster example, not a reconstruction of the original AegisShield cluster configuration. The complete deployment also requires a compatible CNI, ingress controller, Metrics Server, VPA, storage, and authentication components.

Do not install a second CNI on top of an existing one. For a Calico deployment, use the appropriate KinD networking configuration and follow Calico's official installation procedure before deploying application NetworkPolicies.

## Stage 5 — Configure Kubernetes Dependencies

AegisShield requires:

- A NetworkPolicy-enforcing CNI such as Calico
- Metrics Server for HPA
- VPA CRDs and controllers
- NGINX Ingress Controller
- StorageClass and persistent storage
- Keycloak and OAuth2 Proxy
- Required Kubernetes Secrets

Official installation references:

- Calico: https://docs.tigera.io/calico/latest/getting-started/kubernetes/kind
- Metrics Server: https://github.com/kubernetes-sigs/metrics-server
- VPA: https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler
- ingress-nginx: https://kubernetes.github.io/ingress-nginx/deploy/

After installing the required components, verify:

```bash
kubectl get pods -A

kubectl get storageclass

kubectl get apiservice | grep metrics

kubectl get crd | grep verticalpodautoscalers

kubectl get ingressclass
```

Check resource metrics:

```bash
kubectl top nodes

kubectl top pods -A
```

The exact installation commands for these external dependencies depend on the versions and configuration selected for your cluster.

## Stage 6 — Configure Namespaces and Secrets

Create the application namespaces using the repository manifest:

```bash
kubectl apply -f manifests/00-namespaces.yaml
```

Verify:

```bash
kubectl get namespaces
```

Expected application namespaces include:

```text
aegis-app
aegis-data
aegis-edge
```

Review the example Secrets configuration:

```bash
cat config/secrets-example.yaml
```

Provision the required database and application credentials using your chosen secret-management method.

Do not commit actual passwords, tokens, TLS private keys, or other credentials to GitHub.

Verify Secret names without displaying their values:

```bash
kubectl -n aegis-app get secrets

kubectl -n aegis-data get secrets
```

## Stage 7 — Build and Load the Payment API

The working Stage 7 backend image was:

`aegisshield/payment-api:1.0.3`

Build the image from the project root:

```bash
docker build \
  -t aegisshield/payment-api:1.0.3 \
  ./payment-api
```

Verify:

```bash
docker images aegisshield/payment-api
```

Load the image into KinD:

```bash
kind load docker-image \
  aegisshield/payment-api:1.0.3 \
  --name aegisshield-cluster
```

The API image must be built from the actual `payment-api/` source files in the repository.

## Stage 8 — Validate and Deploy the Helm Chart

Validate the chart:

```bash
helm lint ./charts/aegisshield
```

Render Kubernetes resources:

```bash
helm template aegisshield ./charts/aegisshield \
  -n aegis-app \
  -f ./charts/aegisshield/values-local.yaml
```

Install the application with the verified local API image:

```bash
helm upgrade --install aegisshield \
  ./charts/aegisshield \
  -n aegis-app \
  -f ./charts/aegisshield/values-local.yaml \
  --set-string api.image=aegisshield/payment-api:1.0.3 \
  --wait \
  --timeout 5m
```

This requires the chart's database Secrets, storage, networking, and other dependencies to be configured beforehand.

Check Helm:

```bash
helm list -n aegis-app

helm status aegisshield -n aegis-app

helm history aegisshield -n aegis-app
```

Verify deployments:

```bash
kubectl -n aegis-app get deployments

kubectl -n aegis-app get pods -o wide

kubectl -n aegis-app get services

kubectl -n aegis-data get statefulset,pvc
```

## Stage 9 — Verify PostgreSQL

Check PostgreSQL:

```bash
kubectl -n aegis-data get pods

kubectl -n aegis-data get pvc
```

Connect to the database and list tables:

```bash
kubectl -n aegis-data exec postgres-0 -- \
  psql -U aegis_user -d aegis -c '\dt'
```

Check the payments table:

```bash
kubectl -n aegis-data exec postgres-0 -- \
  psql -U aegis_user -d aegis \
  -c "SELECT payment_id, amount, currency, status, created_at
      FROM public.payments
      ORDER BY created_at DESC
      LIMIT 5;"
```

The working Stage 7 application stores simulated payment records in `public.payments`.

## Stage 10 — Verify FastAPI

Start an API port-forward:

```bash
kubectl -n aegis-app port-forward svc/payment-api 8080:80
```

In another terminal, check API readiness:

```bash
curl http://localhost:8080/health/ready
```

Expected healthy response:

```json
{
  "status": "ready",
  "database": "connected"
}
```

Create a simulated payment:

```bash
curl -i -X POST http://localhost:8080/pay \
  -H "Content-Type: application/json" \
  -d '{"amount":10.00,"currency":"EUR"}'
```

Retrieve a payment:

```bash
curl http://localhost:8080/payments/PAYMENT_UUID
```

Replace `PAYMENT_UUID` with the ID returned by the creation request.

## Stage 11 — Access the Payment Dashboard

Start the frontend port-forward:

```bash
kubectl -n aegis-app port-forward svc/frontend 8082:80
```

Open the browser:

**http://localhost:8082**

<img width="394" height="257" alt="{EFB89391-8F0C-4E69-8E8A-557ECFE370F7}" src="https://github.com/user-attachments/assets/0d72f885-a975-447c-aae3-e9e52fae1ac8" />


The dashboard provides:

- Create Test Payment
- Amount and currency selection
- Submit Test Payment
- Payment UUID and status display
- Find Payment
- Retrieve Payment

### Create a Payment

1. Open `http://localhost:8082`.
2. Enter `10.00`.
3. Select `EUR`.
4. Click **Submit Test Payment**.
5. Copy the generated payment UUID.

The frontend calls:

`POST http://localhost:8082/api/pay`

Test with curl:

```bash
curl -i -X POST http://localhost:8082/api/pay \
  -H "Content-Type: application/json" \
  -d '{"amount":10.00,"currency":"EUR"}'
```

### Retrieve a Payment

1. Open `http://localhost:8082`.
2. Enter the generated UUID under **Find Payment**.
3. Click **Retrieve Payment**.

The frontend calls:

`GET http://localhost:8082/api/payments/{payment_id}`

Test with curl:

```bash
curl http://localhost:8082/api/payments/PAYMENT_UUID
```

Replace `PAYMENT_UUID` with the generated UUID.

### Verified Example

A simulated payment successfully created and retrieved during Stage 7:

| Field | Value |
|---|---|
| Payment ID | `30f027a1-df95-4b12-a0aa-21ff7ac07d8d` |
| Amount | 10.00 EUR |
| Status | `simulated_success` |
| Created | 2026-11-07 12:44:47 UTC |

This demonstrates successful communication between the frontend, API, and PostgreSQL database.

## Stage 12 — Verify NetworkPolicies

Check application policies:

```bash
kubectl -n aegis-app get networkpolicy

kubectl -n aegis-data get networkpolicy
```

Inspect the frontend-to-API policies:

```bash
kubectl -n aegis-app describe networkpolicy \
  frontend-allow-payment-api-egress

kubectl -n aegis-app describe networkpolicy \
  api-allow-frontend-ingress
```

Permitted application traffic:

```text
NGINX Frontend
      |
      | TCP 8080
      v
Payment API
      |
      | TCP 5432
      v
PostgreSQL
```

A full zero-trust verification must also test denied connections from unauthorized pods.

## Stage 13 — Verify Authentication and Ingress

Check ingress resources:

```bash
kubectl get ingress -A

kubectl -n aegis-edge get pods,services
```

Inspect the application ingress:

```bash
kubectl -n aegis-app describe ingress
```

The project includes Keycloak and OAuth2 Proxy authentication.

The authenticated ingress must be tested using the configured hostname, DNS, TLS certificate, and identity-provider credentials.

**Security note:** Kubernetes port-forwarding bypasses ingress authentication. Do not expose the localhost dashboard as a production payment service.

## Stage 14 — Verify HPA and VPA

Check HPA:

```bash
kubectl -n aegis-app get hpa

kubectl -n aegis-app describe hpa frontend

kubectl -n aegis-app describe hpa payment-api
```

Configured Stage 7 scaling limits:

| Workload | Minimum | Maximum | CPU Target |
|---|---:|---:|---:|
| Frontend | 3 | 4 | 65% |
| Payment API | 3 | 5 | 65% |

Check VPA:

```bash
kubectl get vpa -A

kubectl -n aegis-app describe vpa payment-api
```

VPA is configured with `updateMode: Off`, providing recommendations without automatically changing container resources.

## Stage 15 — Verify Rollouts and Self-Healing

Check rollout status:

```bash
kubectl -n aegis-app rollout status deployment/frontend

kubectl -n aegis-app rollout status deployment/payment-api
```

Check pod health:

```bash
kubectl -n aegis-app get pods -o wide
```

Inspect logs:

```bash
kubectl -n aegis-app logs deployment/payment-api --tail=100

kubectl -n aegis-app logs deployment/frontend --tail=100
```

Review Kubernetes events:

```bash
kubectl -n aegis-app get events \
  --sort-by=.metadata.creationTimestamp
```

For controlled self-healing tests, delete a selected noncritical application pod only after confirming sufficient replicas and application availability.

## Stage 16 — Verify Helm Upgrade and Rollback

Check release history:

```bash
helm history aegisshield -n aegis-app
```

Check the current image:

```bash
kubectl -n aegis-app get deployment payment-api \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

Validate before an upgrade:

```bash
helm lint ./charts/aegisshield
```

Use a reviewed Helm upgrade with an explicit image version and rollout checks.

If a release fails and rollback is required, review the release history and select a known-good revision:

```bash
helm rollback aegisshield REVISION \
  -n aegis-app \
  --wait \
  --timeout 5m
```

Replace `REVISION` with the intended known-good revision.

Do not blindly roll back database schema changes or persistent data.

## Stage 17 — Final Health Verification

Run:

```bash
kubectl get nodes

kubectl -n aegis-app get deployments,services,hpa

kubectl -n aegis-app get networkpolicy

kubectl -n aegis-data get statefulset,pvc

kubectl get vpa -A

helm status aegisshield -n aegis-app
```

With the frontend port-forward running:

```bash
curl -i http://localhost:8082/

curl -i http://localhost:8082/api/health/ready
```

The dashboard should load, and the API readiness endpoint should confirm database connectivity.

## Stage 18 — Push Changes to GitHub

Check the repository:

```bash
git status --short

git diff --check
```

Stage the intended application and documentation files:

```bash
git add README.md \
  frontend/index.html \
  charts/aegisshield/templates/01-config.yaml \
  charts/aegisshield/templates/04-network-policies.yaml
```

Review:

```bash
git diff --cached --stat

git diff --cached --check
```

Commit:

```bash
git commit -m "docs: add complete AegisShield setup and verification guide"
```

Push:

```bash
git push origin main
```

Repository:

https://github.com/harisamjad0158/AegisShield-project

## Stage 19 — Optional Cleanup

Stop local port-forwards with `Ctrl+C` in their terminals.

To uninstall the Helm application:

```bash
helm uninstall aegisshield -n aegis-app
```

**Warning:** Helm uninstall can remove application resources. Persistent database volumes and data require separate handling and should not be deleted without a backup.

To delete the entire local KinD cluster:

```bash
kind delete cluster --name aegisshield-cluster
```

**Warning:** Deleting the KinD cluster destroys the local Kubernetes environment and may destroy locally stored database data.

## Stage 20 — Planned GitHub Actions CI/CD

The next project phase will add automated tests, GitHub Actions, security scanning, versioned container publishing, and controlled Kubernetes deployments.

These features are planned and have not yet been implemented.

## Security and Production Limitations

AegisShield is not production-ready. Real financial transactions would require stronger authentication, authorization, TLS, secure secret management, database backups, high availability, payment idempotency, audit trails, payment-provider integration, PCI DSS assessment, and additional security validation.

NetworkPolicies provide network segmentation but do not replace authentication or encryption.

---

**AegisShield — Kubernetes, Helm, Zero-Trust Networking, Autoscaling, DevSecOps, and Cloud-Native Application Engineering.**
