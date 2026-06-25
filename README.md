# AI Inference Autoscaling System — Documentation

## Overview

A Kubernetes-based ML inference pipeline that classifies images using ResNet18, with a custom autoscaler that dynamically scales replicas based on real-time latency and queue depth — benchmarked against standard Kubernetes HPA.


---

## Architecture

```
                    Kubernetes Cluster (Minikube)
                    ┌──────────────────────────────────────┐
                    │                                      │
Load Tester ───────►│  Dispatcher  ───►  ResNet Replicas    │
(load_tester.py)    │  (FastAPI)        (1 to 6 pods)      │
                    │  - Queue                              │
                    │  - 7 workers                          │
                    │  - Metrics                            │
                    └──────────┬───────────────────────────┘
                               │
                    ┌──────────▼───────────┐
                    │     Prometheus        │
                    │  (scrapes dispatcher) │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  Custom Autoscaler     │
                    │  (queries Prometheus,  │
                    │   scales via K8s API)  │
                    └───────────────────────┘
```

---

## Components

### 1. `model_server.py` — ResNet18 Inference Server
- Loads ResNet18 (ImageNet weights) via PyTorch/torchvision
- Exposes `POST /infer` — accepts base64-encoded image, returns top-5 predicted labels
- Runs on port `8001`

### 2. `dispatcher.py` — Request Dispatcher
- FastAPI service that sits between clients and resnet-server
- Exposes `POST /predict` — accepts image upload, forwards to resnet-server
- Uses an `asyncio.Queue` + 7 background workers to process requests
- Runs on port `5000`

### 3. `custom_autoscaler.py` — Custom Autoscaler
- Polls Prometheus every 5 seconds for:
  - `dispatcher_queue_size` (queue length)
  - `dispatcher_p99_latency_seconds` (rolling p99 latency)
- Scaling logic:
  - **Scale up** if queue > 2 OR p99 latency > 0.45s (cooldown: 15s)
  - **Scale down** if queue == 0 AND p99 latency < 0.35s (cooldown: 30s)
  - Scales by +3 replicas if severely overloaded (p99 > 1.0s or queue > 5), else +1
- Replicas bounded between `MIN_REPLICAS=1` and `MAX_REPLICAS=6`
- Uses the Kubernetes Python client to patch `resnet-deployment`'s replica count

### 4. `load_tester.py` — Load Testing Tool
- Replays `workload.txt` (one number per line = target concurrent users for that second)
- Picks a random image from `imagenet-sample-images/` per request
- Tracks:
  - Client-side latency (request → response, end to end)
  - Server-side p99 latency (queried from Prometheus, sampled every 5s)
  - Live replica count (via `kubectl`)
- Outputs:
  - `custom_results.csv` — every request's latency + status
  - `custom_replicas.csv` — replica count + server p99 over time

### 5. `compare_results.py` — Results Comparison
- Loads result CSVs from multiple runs (custom autoscaler, HPA70, HPA90)
- Plots:
  - `compare_latency.png` — server-side p99 over time, all runs overlaid
  - `compare_replicas.png` — replica count over time, all runs overlaid
- Prints a summary table: total requests, success rate, max server p99, target met (Y/N)

### 6. `k8s.yaml` — Kubernetes Manifests
Defines all deployments and services:
- `resnet-deployment` + `resnet-server` (ClusterIP service)
- `dispatcher` + `dispatcher` (NodePort service, fixed port `30001`)
- `prometheus` + ConfigMap (scrapes dispatcher every 15s)
- `custom-autoscaler` + ServiceAccount + RBAC (Role/RoleBinding to patch deployments)

### 7. `hpa.yaml` — Kubernetes HPA (for comparison)
- Standard Kubernetes HorizontalPodAutoscaler targeting `resnet-deployment`
- Scales 1–6 replicas based on CPU utilization (`averageUtilization: 70` or `90`)
- Used only for benchmarking against the custom autoscaler — not used at the same time as `custom-autoscaler`

---

## Prerequisites

- Docker Desktop (with WSL2 backend, sufficient memory/CPU allocated via `.wslconfig`)
- Minikube
- kubectl
- Python 3.11+
- A Docker Hub account (to host your built images)

---

## Setup — First Time

### 1. Configure Docker Desktop resources (Windows + WSL2)

Edit `%USERPROFILE%\.wslconfig`:
```ini
[wsl2]
memory=8GB
processors=8
swap=2GB
```

Restart:
```powershell
wsl --shutdown
```
Then fully quit and reopen Docker Desktop.

### 2. Start Minikube
```powershell
minikube start --cpus=8 --memory=7g
```

### 3. Build and push all images
```powershell
cd model_server
docker build -t 1zhann/ai-model-server:latest ./model_server
docker push 1zhann/ai-model-server:latest


cd dispatcher
docker build -t 1zhann/ai-dispatcher:latest ./dispatcher
docker push 1zhann/ai-dispatcher:latest

cd autoscaler
docker build -t 1zhann/custom-autoscaler:latest ./autoscaler
docker push 1zhann/custom-autoscaler:latest
```

### 4. Deploy everything
```powershell
cd deployments
kubectl apply -f k8s.yaml
kubectl get pods -w
```

Wait until all pods show `1/1 Running` before proceeding.

---
### 5. Clone the imagenet repo and save it as imagenet-sample-images
git clone https://github.com/EliSchwartz/imagenet-sample-images
save this repo as "imagenet-sample-images" in the same folder



## Running a Test — Custom Autoscaler

```powershell
# Terminal 1 — keep open
kubectl port-forward service/prometheus 9090:9090

# Terminal 2 — keep open
kubectl port-forward service/dispatcher 5000:5000

#Terminal 3 - keep open
minikube service dispatcher-service --url
update the url in load_tester.py

# Terminal 3 — run the test
py load_tester.py
```

Results are saved to `custom_results.csv` and `custom_replicas.csv`.

---

## Running a Test — HPA Comparison

### 1. Disable custom autoscaler
```powershell
kubectl delete deployment custom-autoscaler
```

### 2. Enable metrics-server (required for HPA)
```powershell
minikube addons enable metrics-server
```

### 3. Deploy HPA at 70%
Ensure `hpa.yaml` has `averageUtilization: 70`, then:
```powershell
kubectl apply -f deployments/hpa70.yaml
kubectl get hpa
```

### 4. Run the test, rename outputs
```powershell
rename the output files as "hpa70_results.csv" abd "hpa70_replicase.csv" in load_tester.py
py load_tester.py
```

### 5. Repeat for HPA90
rename the output files as "hpa90_results.csv" abd "hpa90_replicase.csv" in load_tester.py
Run the same experiment for hpa90



## Comparing Results

Once you have `custom_*.csv`, `hpa70_*.csv`, and `hpa90_*.csv` in the same folder:

```powershell
pip install matplotlib pandas
py compare_results.py
```

This generates `compare_latency.png`, `compare_replicas.png`, and prints a summary table to the console.

---

## Key Metrics Reference (Prometheus)

Access via:
```powershell
kubectl port-forward service/prometheus 9090:9090
```
Then open `http://localhost:9090` and query:

| Metric | Description |
|---|---|
| `dispatcher_requests_total` | Total requests received by dispatcher |
| `dispatcher_queue_size` | Current queue depth |
| `dispatcher_p99_latency_seconds` | Rolling p99 latency (dispatcher's view, ~server-side) |
| `dispatcher_request_latency_seconds_bucket` | Histogram, use with `histogram_quantile()` for custom percentiles |

Example query for p95 latency:
```
histogram_quantile(0.95, rate(dispatcher_request_latency_seconds_bucket[1m]))
```

---

## Useful Commands Reference

```powershell
# Pod status
kubectl get pods -w

# Logs
kubectl logs -l app=dispatcher -f
kubectl logs -l app=custom-autoscaler -f
kubectl logs -l app=resnet-server --tail=30

# Replica count
kubectl get deployment resnet-deployment -o jsonpath="{.status.readyReplicas}"

# Restart a component
kubectl delete deployment dispatcher
kubectl apply -f k8s.yaml

# Get dispatcher's accessible URL (if not using port-forward)
minikube service dispatcher --url
```

---



**Conclusion:** The custom autoscaler, which reacts directly to latency and queue depth, scales more aggressively and keeps server-side latency within target far more consistently than standard CPU-based HPA — which never scaled past 3 replicas because CPU utilization alone was not a reliable proxy for actual request latency under this workload.