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
                        │   ┌─────────────┐    ┌──────────────┐  │
Load Tester (Locust) ───┼──►│  Dispatcher │───►│   Replica 1  │  │
                        │   │  (FastAPI)  │    ├──────────────┤  │
                        │   │             │───►│   Replica 2  │  │
                        │   │  - Queue    │    ├──────────────┤  │
                        │   │  - LB       │───►│   Replica N  │  │
                        │   └─────────────┘    └──────────────┘  │
                        │                             │           │
                        │   ┌─────────────┐           │           │
                        │   │ Prometheus  │◄──────────┘           │
                        │   │ Monitoring  │                       │
                        │   └─────────────┘                       │
                        │         │                               │
                        │   ┌─────────────┐    ┌──────────────┐  │
                        │   │ Autoscaler  │───►│  API Server  │  │
                        │   │ (HPA/Custom)│    │ (Kubernetes) │  │
                        │   └─────────────┘    └──────────────┘  │
                        └─────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
ai_assignment/
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
- Deployed to Minikube with a Kubernetes **Deployment** and **NodePort Service**
- Configured CPU/memory limits (`1 CPU`, `1G RAM`) per replica
- Verified inference works end-to-end using `client.py`

### Phase 3 — Dispatcher Deployment ✅
- Built a **FastAPI dispatcher** with:
  - Async request queue (`asyncio.Queue`)
  - Concurrent background workers
  - Image preprocessing (resize to 256x256, base64 encode)
  - Forwarding to resnet-server Kubernetes service
- Containerized and pushed dispatcher image to Docker Hub
- Deployed dispatcher to Minikube as a separate Deployment + Service
- Locust load tester configured to send requests to dispatcher

---

## 🔲 Upcoming

### Phase 4 — Monitoring with Prometheus
- Install Prometheus inside the Kubernetes cluster
- Expose metrics from dispatcher (queue size, request latency, throughput)
- Visualize with Grafana dashboard

### Phase 5 — Autoscaling
- Configure **Kubernetes HPA** (Horizontal Pod Autoscaler) based on CPU usage
- Build a **Custom Autoscaler** based on queue depth and latency metrics from Prometheus
- Both autoscalers talk to the Kubernetes API Server to scale replicas up/down

### Phase 6 — Load Testing & Comparison
- Run Locust with increasing user loads
- Benchmark **HPA vs Custom Autoscaler**:
  - Response latency
  - Throughput (requests/sec)
  - Scaling speed (how fast new pods come up)
- **Success criteria: p95 latency < 0.5 seconds**

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

# Deploy model server + dispatcher
kubectl apply -f k8s.yaml

# Wait for pods to be ready
kubectl rollout status deployment/resnet-server
kubectl rollout status deployment/dispatcher
```

### Run the load tester

```bash
# Forward dispatcher port
kubectl port-forward service/dispatcher 5000:5000

# Start Locust
locust -f locust/locustfile.py --host=http://localhost:5000
# Open http://localhost:8089
```

---

## 🛠️ Tech Stack

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
