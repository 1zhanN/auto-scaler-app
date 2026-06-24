"""
Compare Custom Autoscaler vs HPA70 vs HPA90

Expects these files in the current folder (from your three test runs):
  custom_results.csv,  custom_replicas.csv
  hpa70_results.csv,   hpa70_replicas.csv
  hpa90_results.csv,   hpa90_replicas.csv

Usage:
    py compare_results.py
"""

import pandas as pd
import matplotlib.pyplot as plt

RUNS = {
    "Custom": ("custom_results.csv", "custom_replicas.csv"),
    "HPA70": ("hpa70_results.csv", "hpa70_replicas.csv"),
    "HPA90": ("hpa90_results.csv", "hpa90_replicas.csv"),  # not run yet
}

COLORS = {"Custom": "tab:green", "HPA70": "tab:blue", "HPA90": "tab:orange"}

data = {}
for name, (results_file, replicas_file) in RUNS.items():
    try:
        results = pd.read_csv(results_file)
        replicas = pd.read_csv(replicas_file)
        data[name] = {"results": results, "replicas": replicas}
        print(f"Loaded {name}: {len(results)} requests, {len(replicas)} samples")
    except FileNotFoundError as e:
        print(f"Skipping {name}: {e}")

if not data:
    raise SystemExit("No result files found. Run the load tests first.")

# ── Plot 1: Server-side p99 latency over time ─────────────────────────────────
plt.figure(figsize=(12, 5))
for name, d in data.items():
    plt.plot(d["replicas"]["second"], d["replicas"]["server_p99"],
              label=name, color=COLORS.get(name), marker="o", markersize=3)
plt.axhline(y=0.5, color="red", linestyle="--", label="Target (0.5s)")
plt.xlabel("Time (s)")
plt.ylabel("Server-side p99 latency (s)")
plt.title("Server-side Latency: Custom Autoscaler vs HPA70 vs HPA90")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("compare_latency.png", dpi=150)
print("Saved compare_latency.png")

# ── Plot 2: Replica count over time ───────────────────────────────────────────
plt.figure(figsize=(12, 5))
for name, d in data.items():
    plt.step(d["replicas"]["second"], d["replicas"]["replicas"],
              label=name, color=COLORS.get(name), where="post")
plt.xlabel("Time (s)")
plt.ylabel("Replica count")
plt.title("Replica Scaling: Custom Autoscaler vs HPA70 vs HPA90")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("compare_replicas.png", dpi=150)
print("Saved compare_replicas.png")

# ── Summary table ──────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print(f"{'Run':<10} {'Total':>8} {'Success':>8} {'Fail':>8} {'SuccessRate':>12} "
      f"{'ServerP99Max':>14} {'ServerP99 < 0.5s':>18}")
print("-" * 80)

for name, d in data.items():
    results = d["results"]
    replicas = d["replicas"]

    total = len(results)
    success = len(results[results["status"] == "200"]) if results["status"].dtype == object \
        else len(results[results["status"] == 200])
    fail = total - success
    success_rate = success / total * 100 if total else 0

    server_p99_max = replicas["server_p99"].max()
    target_met = "YES" if server_p99_max < 0.5 else "NO"

    print(f"{name:<10} {total:>8} {success:>8} {fail:>8} {success_rate:>11.2f}% "
          f"{server_p99_max:>14.3f} {target_met:>18}")

print("=" * 80)