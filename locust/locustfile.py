from locust import HttpUser, task, between
import cv2
import base64
import json
import numpy as np
import io

class ResNetUser(HttpUser):
    wait_time = between(1, 3)  # each user waits 1-3 seconds between requests

    @task
    def predict(self):
        # Read and resize image
        im = cv2.imread("fluki.png")
        im = cv2.resize(im, dsize=(256, 256), interpolation=cv2.INTER_CUBIC)
        
        # Encode to JPEG bytes
        _, buffer = cv2.imencode(".jpeg", im)
        image_bytes = io.BytesIO(buffer.tobytes())

        # Send as multipart form (matches your dispatcher's UploadFile endpoint)
        self.client.post(
            "/predict",
            files={"image": ("fluki.png", image_bytes, "image/jpeg")}
        )