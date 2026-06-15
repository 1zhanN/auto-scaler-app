from fastapi import FastAPI, UploadFile, File
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import FastAPI, UploadFile, File, Response
import httpx
import cv2
import base64
import numpy as np
import io
import asyncio
from collections import deque
import time

app = FastAPI()

# Prometheus metrics
REQUEST_COUNT = Counter('dispatcher_requests_total', 'Total requests received')
REQUEST_LATENCY = Histogram('dispatcher_request_latency_seconds', 'Request latency')
QUEUE_SIZE = Gauge('dispatcher_queue_size', 'Current queue size')
ACTIVE_WORKERS = Gauge('dispatcher_active_workers', 'Active worker threads')

RESNET_URL = "http://resnet-server:8001/infer"
queue = asyncio.Queue()
MAX_CONCURRENT = 4

async def worker():
    """Continuously pulls from queue and sends to resnet pods"""
    while True:
        image_data, future = await queue.get()
        ACTIVE_WORKERS.inc()
        try:
            start = time.time()
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    RESNET_URL,
                    content=image_data,
                    headers={"Content-Type": "application/json"}
                )
                latency = time.time() - start
                REQUEST_LATENCY.observe(latency)
                future.set_result(response.json())
        except Exception as e:
            future.set_exception(e)
        finally:
            ACTIVE_WORKERS.dec()
            queue.task_done()

@app.on_event("startup")
async def startup():
    for _ in range(MAX_CONCURRENT):
        asyncio.create_task(worker())

@app.post("/predict")
async def predict(image: UploadFile = File(...)):
    REQUEST_COUNT.inc()
    QUEUE_SIZE.set(queue.qsize())
    
    contents = await image.read()
    img_array = np.frombuffer(contents, np.uint8)
    im = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    im = cv2.resize(im, dsize=(256, 256), interpolation=cv2.INTER_CUBIC)

    encoded = base64.b64encode(
        cv2.imencode(".jpeg", im)[1].tobytes()
    ).decode("utf-8")

    import json
    payload = json.dumps({"data": encoded}).encode()

    loop = asyncio.get_event_loop()
    future = loop.create_future()
    await queue.put((payload, future))

    result = await future
    return result

@app.get("/metrics")
async def metrics():
    """Expose Prometheus metrics"""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from fastapi.responses import Response
    
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
@app.get("/queue-size")
async def queue_size():
    return {"queue_size": queue.qsize()}