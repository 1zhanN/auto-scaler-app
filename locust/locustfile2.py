from locust import HttpUser, task, between, LoadTestShape
import os
import random

IMAGE_DIR = "test_images"

images = []
for fname in os.listdir(IMAGE_DIR):
    if fname.lower().endswith((".jpeg", ".jpg", ".png", ".JPEG")):
        fpath = os.path.join(IMAGE_DIR, fname)
        with open(fpath, "rb") as f:
            images.append((fname, f.read()))

print(f"Loaded {len(images)} images for testing")


class PredictUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def predict(self):
        fname, data = random.choice(images)
        self.client.post(
            "/predict",
            files={"image": (fname, data, "image/jpeg")}
        )


class BarAzmoonShape(LoadTestShape):
    # Load workload from file — space-separated integers
    workload_file = "workload.txt"

    with open(workload_file, "r") as f:
        workload = list(map(int, f.read().split()))

    print(f"Loaded workload with {len(workload)} seconds")

    def tick(self):
        run_time = int(self.get_run_time())

        if run_time >= len(self.workload):
            return None

        target_rps = self.workload[run_time]

        if target_rps == 0:
            return (0, 1)  # avoid ZeroDivisionError

        return (target_rps, target_rps)