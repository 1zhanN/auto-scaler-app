import requests
import cv2
import base64
import json
import time

im = cv2.imread("fluki.png")
im = cv2.resize(im, dsize=(256, 256), interpolation=cv2.INTER_CUBIC)

# Encode to JPEG bytes
_, buffer = cv2.imencode(".jpeg", im)
image_bytes = buffer.tobytes()

t = time.perf_counter()

# 👇 Send to DISPATCHER (port 5000) as multipart form
response = requests.post(
    "http://localhost:5000/predict",
    files={"image": ("fluki.png", image_bytes, "image/jpeg")}
)

latency = time.perf_counter() - t
print(response.json(), f"Latency: {round(latency, 3)}s")