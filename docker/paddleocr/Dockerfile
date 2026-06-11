FROM python:3.11-slim

WORKDIR /app

# System deps: build tools + PaddlePaddle runtime + OpenCV libGL
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgomp1 \
    libglib2.0-0 \
    libgl1 \
    libglx0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

EXPOSE 5001

CMD ["python", "server.py"]
