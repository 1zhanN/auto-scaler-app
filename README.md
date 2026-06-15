# 🧠 Kubernetes ML Inference System

A scalable machine learning inference pipeline deployed on Kubernetes (Minikube), featuring a ResNet18 image classifier, a custom dispatcher with request queuing, load testing, monitoring, and autoscaling.

---

## 📌 Project Goals

- Deploy a real ML model (ResNet18) as a containerized microservice on Kubernetes
- Build a custom dispatcher to manage request queuing and load balancing across replicas
- Monitor the system using Prometheus
- Implement and compare two autoscaling strategies: **Kubernetes HPA** vs **Custom Autoscaler**
- Load test the system with Locust
- **Target: maintain inference latency under 0.5 seconds**

---

## 🏗️ System Architecture

```
                        Kubernetes Cluster (Minikube)
                        ┌─────────────────────────────────────────┐
                        │                                         │
                        │   ┌─────────────┐    ┌──────────────┐   │
Load Tester (Locust) ───┼──►│  Dispatcher │───►│   Replica 1  │   │
                        │   │  (FastAPI)  │    ├──────────────┤   │
                        │   │             │───►│   Replica 2  │   │
                        │   │  - Queue    │    ├──────────────┤   │
                        │   │  - LB       │───►│   Replica N  │   │
                        │   └─────────────┘    └──────────────┘   │
                        │                             │           │
                        │   ┌─────────────┐           │           │
                        │   │ Prometheus  │◄──────────┘           │
                        │   │ Monitoring  │                       │
                        │   └─────────────┘                       │
                        │         │                               │
                        │   ┌─────────────┐    ┌──────────────┐   │
                        │   │ Autoscaler  │───►│  API Server  │   │
                        │   │ (HPA/Custom)│    │ (Kubernetes) │   │
                        │   └─────────────┘    └──────────────┘   │
                        └─────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
ai_assignment/
├──deployments/
|   ├── k8s.yaml 
├── model_server/
│   ├── model_server.py        # ResNet18 inference server (aiohttp)
│   └── Dockerfile             # Container image for the model
│
├── dispatcher/ 
│   ├── dispatcher.py          # FastAPI dispatcher with async queue
│   ├── Dockerfile             # Container image for dispatcher
│   └── requirements.txt       # Python dependencies
│
├── locust/
│   ├── locustfile.py          # Load test: single image endpoint
│   └── locustfile2.py         # Load test: variant/stress test
│
├── k8s.yaml                   # Kubernetes Deployments + Services
├── client.py                  # Simple test client
├── fluki.png                  # Test image (Samoyed dog 🐕)
└── README.md
```

---

## ✅ Progress

### Phase 1 — Environment Setup ✅
- Installed **Minikube** to run a local Kubernetes cluster
- Installed **kubectl** to manage the cluster
- Set up **Docker** and created a Docker Hub account for image hosting

### Phase 2 — Model Server Deployment ✅
- Built a ResNet18 inference server using PyTorch + aiohttp (`model_server.py`)
- Containerized it with Docker and pushed to Docker Hub
- Deployed to Minikube with a Kubernetes **Deployment** (initially 1 replica)
- Configured CPU/memory limits (`1 CPU`, `1G RAM`) per replica
- Exposed via **ClusterIP Service** (internal-only access)
- Verified inference works end-to-end using `client.py`

### Phase 3 — Dispatcher Deployment ✅
- Built a **FastAPI dispatcher** (`dispatcher.py`) with:
  - Async request queue (`asyncio.Queue`) for buffering incoming requests
  - 4 concurrent background workers to forward to resnet-server
  - Image preprocessing (resize to 256x256, encode to JPEG, base64)
  - Multi-part form handling for file uploads
  - Forwarding to resnet-server Kubernetes service (load-balanced across replicas)
- Containerized with Docker and pushed to Docker Hub
- Deployed dispatcher to Minikube as a separate **Deployment** (1 replica)
- Exposed via **NodePort Service** (accessible from laptop via `localhost:5000`)
- Updated `client.py` to send requests to dispatcher instead of resnet directly
- Verified end-to-end: client → dispatcher → resnet-server

### Phase 4 — Monitoring with Prometheus ✅
- Installed **Prometheus** inside the Kubernetes cluster
- Added **prometheus-client** library to dispatcher
- Exposed metrics from dispatcher (`/metrics` endpoint):
  - `dispatcher_requests_total` — counter of all requests
  - `dispatcher_request_latency_seconds` — histogram of inference time
  - `dispatcher_queue_size` — gauge of current queue depth
  - `dispatcher_active_workers` — gauge of active workers
- Created **ConfigMap** with Prometheus scrape configuration
- Configured Prometheus to scrape dispatcher metrics every 15 seconds
- Verified metrics flow: ran `client.py` multiple times → metrics visible in Prometheus dashboard
- Can query metrics like `dispatcher_requests_total` and see live graphs at `http://localhost:9090`

---

## 🔲 Upcoming

### Phase 5 — Horizontal Pod Autoscaling (HPA)
- Scale resnet-server replicas from 3 to 10 based on **CPU utilization** (70% threshold)
- Scale dispatcher replicas from 1 to 5 based on **CPU utilization**
- Apply `hpa.yaml` with Kubernetes autoscaler
- Test with Locust load tester to trigger scaling events
- Monitor replica count changes in real-time

### Phase 6 — Custom Autoscaler
- Build a Python autoscaler that reads **queue depth** from Prometheus
- Scale resnet-server based on `dispatcher_queue_size` (not just CPU)
- Compare scaling speed vs Kubernetes HPA
- Expected: faster scale-up for queue-based autoscaler

### Phase 7 — Load Testing & Comparison
- Run comprehensive load tests with Locust (gradually increase from 10 to 100+ users)
- Benchmark **HPA vs Custom Autoscaler**:
  - Response latency (p50, p95, p99)
  - Throughput (requests/sec)
  - Scaling speed (time to reach desired replicas)
  - Resource efficiency (CPU/memory usage)
- **Success criteria: p95 latency < 0.5 seconds under sustained load**
- Generate comparison report with graphs

---

## 📊 Current Metrics

These metrics are actively collected from the dispatcher and visible in Prometheus:

| Metric | Type | Description |
|--------|------|-------------|
| `dispatcher_requests_total` | Counter | Total number of prediction requests received |
| `dispatcher_request_latency_seconds` | Histogram | End-to-end latency per request (min, max, quantiles) |
| `dispatcher_queue_size` | Gauge | Current number of requests waiting in the queue |
| `dispatcher_active_workers` | Gauge | Number of worker threads actively processing requests |

**Access Prometheus dashboard:** 
```powershell
kubectl port-forward service/prometheus 9090:9090
# Open http://localhost:9090
```

---

## 🔧 Current Deployment Status

```
Kubernetes Cluster (Minikube)
├── resnet-server (Deployment)
│   ├── Replica 1 (Running)
│   ├── Replica 2 (Running)
│   ├── Replica 3 (Running)
│   └── Service: ClusterIP (internal only)
│
├── dispatcher (Deployment)
│   ├── Replica 1 (Running)
│   └── Service: NodePort (exposed on :5000)
│
├── prometheus (Deployment)
│   ├── Replica 1 (Running)
│   ├── ConfigMap (scrape config)
│   └── Service: NodePort (exposed on :9090)
│
└── All scrape targets: UP ✅
```

---

## 🚀 Getting Started

### Prerequisites
- [Minikube](https://minikube.sigs.k8s.io/docs/start/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Docker](https://www.docker.com/)
- Python 3.11+

### Deploy the cluster

```bash
# Start Minikube
minikube start --cpus=2 --memory=2g

# Deploy all services (resnet-server, dispatcher, prometheus)
kubectl apply -f k8s.yaml

# Wait for all pods to be ready
kubectl get pods -w
```

### Verify metrics are working

```powershell
# Terminal 1: Port-forward dispatcher
kubectl port-forward service/dispatcher 5000:5000

# Terminal 2: Send test requests to generate metrics
py client.py
py client.py
py client.py

# Terminal 3: Port-forward Prometheus and view metrics
kubectl port-forward service/prometheus 9090:9090
# Open http://localhost:9090
# Query: dispatcher_requests_total or dispatcher_request_latency_seconds
```

### Run the load tester

```bash
# Terminal 1: Keep port-forward to dispatcher
kubectl port-forward service/dispatcher 5000:5000

# Terminal 2: Start Locust
locust -f locust/locustfile.py --host=http://localhost:5000
# Open http://localhost:8089

# Terminal 3: Watch metrics in Prometheus
kubectl port-forward service/prometheus 9090:9090
# Query: dispatcher_queue_size (watch it spike during load test)
```

---

## 💻 Important Terminal Commands

### Cluster Management

```powershell
# Start/stop Minikube
minikube start --cpus=2 --memory=2g
minikube stop
minikube delete

# Get cluster info
kubectl cluster-info
minikube status
```

### Pod & Deployment Management

```powershell
# View all pods
kubectl get pods
kubectl get pods -w                    # Watch in real-time

# View all deployments
kubectl get deployments

# View all services
kubectl get services

# Describe a pod (useful for debugging)
kubectl describe pod <pod-name>

# Check pod logs
kubectl logs -l app=dispatcher         # All dispatcher logs
kubectl logs -l app=dispatcher -f      # Follow logs (live)
kubectl logs <pod-name>                # Specific pod

# Scale a deployment manually
kubectl scale deployment dispatcher --replicas=3

# Rollout status
kubectl rollout status deployment/dispatcher
```

### Port Forwarding (for local access)

```powershell
# Dispatcher (to send requests)
kubectl port-forward service/dispatcher 5000:5000

# Prometheus (to view metrics)
kubectl port-forward service/prometheus 9090:9090

# Port forward in background
Start-Job { kubectl port-forward service/dispatcher 5000:5000 }
```

### Autoscaling & HPA

```powershell
# View HPA status
kubectl get hpa
kubectl get hpa -w                     # Watch HPA scaling in real-time

# Describe HPA (shows current/desired replicas)
kubectl describe hpa resnet-hpa

# View metrics used by HPA
kubectl get hpa resnet-hpa --show-metrics
```

### Deployment & Configuration

```powershell
# Apply configurations
kubectl apply -f k8s.yaml
kubectl apply -f deployments/hpa.yaml

# Delete resources
kubectl delete deployment dispatcher
kubectl delete pod <pod-name>
kubectl delete configmap prometheus-config

# Edit resources in-place
kubectl edit deployment dispatcher
```

### Debugging & Metrics

```powershell
# Check resource requests/limits
kubectl describe node

# View current resource usage
kubectl top pods
kubectl top nodes

# Get metrics from Prometheus API (if needed)
kubectl port-forward service/prometheus 9090:9090
# Then curl http://localhost:9090/api/v1/query?query=dispatcher_requests_total
```

### Useful Alias (PowerShell)

Add to your PowerShell profile for faster commands:

```powershell
Set-Alias -Name k -Value kubectl
Set-Alias -Name kgp -Value { kubectl get pods }
Set-Alias -Name kg -Value { kubectl get }
Set-Alias -Name kl -Value { kubectl logs }
```

Then use:
```powershell
k get pods
kgp -w
kl -l app=dispatcher -f
```

---

## 🔗 Quick Access URLs

Once services are port-forwarded:

| Service | URL | Purpose |
|---------|-----|---------|
| Dispatcher | `http://localhost:5000` | Send inference requests |
| Prometheus | `http://localhost:9090` | View metrics & graphs |
| Locust | `http://localhost:8089` | Load testing UI |

---

| Tool | Purpose |
|------|---------|
| PyTorch + ResNet18 | ML inference model |
| aiohttp | Model server |
| FastAPI | Dispatcher API |
| Docker | Containerization |
| Kubernetes (Minikube) | Container orchestration |
| Locust | Load testing |
| Prometheus | Monitoring & metrics |
| Python asyncio | Async request queue |
