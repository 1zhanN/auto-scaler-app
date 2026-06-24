FROM python:3.9

ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY custom_autoscaler.py .
COPY requirements.txt .
RUN pip install -r requirements.txt

CMD ["python", "custom_autoscaler.py"]