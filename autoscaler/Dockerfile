FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    kubernetes \
    requests

COPY custom_autoscaler.py .

CMD ["python", "custom_autoscaler.py"]