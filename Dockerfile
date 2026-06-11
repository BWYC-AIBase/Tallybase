FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TALLY_DATA_DIR=/data

WORKDIR /app

COPY gateway/requirements.txt /app/gateway/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/gateway/requirements.txt

COPY gateway /app/gateway
RUN mkdir -p /data

WORKDIR /app/gateway

EXPOSE 5000
VOLUME ["/data"]

CMD ["python", "tally_gateway.py"]
