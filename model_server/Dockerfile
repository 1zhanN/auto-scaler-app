# 1. Use a stable, slim Linux image with Python 3.11
FROM python:3.11-slim

# 2. Set the internal folder where the app will live
WORKDIR /app

# 3. Prevent Python from buffering stdout and stderr (helps with logging)
ENV PYTHONUNBUFFERED=1

# 4. Install system dependencies for OpenCV and clean up to keep image small
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*
# 5. Copy the requirements file
COPY requirements.txt .

# 6. Install libraries (including torch/torchvision for CPU)
RUN pip install --no-cache-dir -r requirements.txt

# 7. Copy your server code
COPY model_server.py .

# 8. Open the port for communication
EXPOSE 8001

# 9. Start the server
CMD ["python", "model_server.py"]