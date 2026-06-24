import requests
import cv2
import time
import threading
import csv
import subprocess
import os
import random

# ── Config ───────────────────────────────────────────────────────────────────
DISPATCHER_URL = "http://127.0.0.1:53864/predict"   # update with your port-forward URL
PROMETHEUS_URL = "http://127.0.0.1:9090"            # update if different
WORKLOAD_FILE  = "workload.txt"
IMAGE_DIR      = "./imagenet-sample-images"          # folder of real images
RESULTS_FILE   = "hpa90_results.csv"
REPLICAS_FILE  = "hpa90_replicas.csv"

# ── Load workload ─────────────────────────────────────────────────────────────
with open(WORKLOAD_FILE) as f:
    WORKLOAD = [int(x) for x in f.read().split()]

# ── Load images ───────────────────────────────────────────────────────────────
image_paths = [
    os.path.join(IMAGE_DIR, f)
    for f in os.listdir(IMAGE_DIR)
    if f.lower().endswith((".jpg", ".jpeg", ".png"))
]
if not image_paths:
    raise RuntimeError(f"No images found in {IMAGE_DIR}")
print(f"Loaded {len(image_paths)} images from {IMAGE_DIR}")

# Pre-encode every image once at startup, so workers aren't doing disk/cv2 work
# during the test itself.
ENCODED_IMAGES = []
for p in image_paths:
    im = cv2.imread(p)
    if im is None:
        continue
    im = cv2.resize(im, dsize=(256, 256), interpolation=cv2.INTER_CUBIC)
    _, buffer = cv2.imencode(".jpeg", im)
    ENCODED_IMAGES.append(buffer.tobytes())

if not ENCODED_IMAGES:
    raise RuntimeError(f"No valid images could be read from {IMAGE_DIR}")

# ── Shared state ──────────────────────────────────────────────────────────────
results = []           # client-side request results
replica_records = []   # replicas + server-side latency, sampled every 5s
lock = threading.Lock()
active_workers = []    # (thread, stop_event) for persistent simulated users
_stop_tracking = threading.Event()


def _get_replicas():
    try:
        out = subprocess.check_output(
            ["kubectl", "get", "deployment", "resnet-deployment",
             "-o", "jsonpath={.status.readyReplicas}"],
            stderr=subprocess.DEVNULL
        )
        val = out.decode().strip()
        return int(val) if val else 0
    except Exception:
        return 0


def _get_server_p99():
    """Server-side p99 latency, read from dispatcher's Prometheus gauge"""
    try:
        r = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": "dispatcher_p99_latency_seconds"},
            timeout=3
        )
        result = r.json()["data"]["result"]
        return float(result[0]["value"][1]) if result else 0.0
    except Exception:
        return -1.0


def _track_replicas(start_time):
    while not _stop_tracking.is_set():
        elapsed = round(time.time() - start_time)
        replica_records.append({
            "second": elapsed,
            "replicas": _get_replicas(),
            "server_p99": _get_server_p99()
        })
        time.sleep(5)


# ── Persistent simulated user ─────────────────────────────────────────────────
def user_loop(stop_event):
    while not stop_event.is_set():
        t_start = time.time()
        try:
            image_bytes = random.choice(ENCODED_IMAGES)
            r = requests.post(
                DISPATCHER_URL,
                files={"image": ("test.jpg", image_bytes, "image/jpeg")},
                timeout=10
            )
            latency = time.time() - t_start
            with lock:
                results.append({"latency": latency, "status": r.status_code})
        except Exception as e:
            latency = time.time() - t_start
            with lock:
                results.append({"latency": latency, "status": f"error: {e}"})
        time.sleep(0.05)


def set_active_users(target):
    current = len(active_workers)
    if target > current:
        for _ in range(target - current):
            stop_event = threading.Event()
            t = threading.Thread(target=user_loop, args=(stop_event,), daemon=True)
            t.start()
            active_workers.append((t, stop_event))
    elif target < current:
        for _ in range(current - target):
            t, stop_event = active_workers.pop()
            stop_event.set()


def stop_all_users():
    for t, stop_event in active_workers:
        stop_event.set()
    for t, _ in active_workers:
        t.join(timeout=2)


# ── Main loop ─────────────────────────────────────────────────────────────────
print(f"Starting load test: {len(WORKLOAD)} seconds, peak {max(WORKLOAD)} concurrent users")
print(f"Targeting: {DISPATCHER_URL}\n")

test_start = time.time()
tracker = threading.Thread(target=_track_replicas, args=(test_start,), daemon=True)
tracker.start()

for second, target_users in enumerate(WORKLOAD):
    set_active_users(target_users)
    replicas_now = _get_replicas()
    print(f"[s={second:>3}] target_users={target_users:>2} replicas={replicas_now}")
    time.sleep(1.0)

print("\nWinding down simulated users...")
stop_all_users()
_stop_tracking.set()
time.sleep(1)

# ── Calculate results ─────────────────────────────────────────────────────────
successful = [r for r in results if r["status"] == 200]
failed = [r for r in results if r["status"] != 200]
successful_latencies = [r["latency"] for r in successful]

print(f"\n--- Final Results ---")
print(f"Total requests:  {len(results)}")
print(f"Successful:      {len(successful)}")
print(f"Failed:          {len(failed)}")

if successful_latencies:
    sorted_lat = sorted(successful_latencies)
    p50 = sorted_lat[int(len(sorted_lat) * 0.50) - 1]
    p99 = sorted_lat[int(len(sorted_lat) * 0.99) - 1]
    avg = sum(successful_latencies) / len(successful_latencies)
    print(f"\nCLIENT-SIDE latency:")
    print(f"  Average: {avg:.3f}s")
    print(f"  P50:     {p50:.3f}s")
    print(f"  P99:     {p99:.3f}s")

server_p99_final = _get_server_p99()
print(f"\nSERVER-SIDE p99 (final reading): {server_p99_final:.3f}s")
status = "PASS" if 0 <= server_p99_final < 0.5 else "FAIL"
print(f"TARGET (server p99 < 0.5s): {status}")

if failed:
    print(f"\nFailed request reasons:")
    reasons = {}
    for r in failed:
        reasons[r["status"]] = reasons.get(r["status"], 0) + 1
    for reason, count in reasons.items():
        print(f"  {reason}: {count}")

# ── Save results ───────────────────────────────────────────────────────────────
with open(RESULTS_FILE, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["latency", "status"])
    writer.writeheader()
    writer.writerows(results)
print(f"\nLatency results saved to {RESULTS_FILE}")

with open(REPLICAS_FILE, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["second", "replicas", "server_p99"])
    writer.writeheader()
    writer.writerows(replica_records)
print(f"Replica + server-latency records saved to {REPLICAS_FILE}")