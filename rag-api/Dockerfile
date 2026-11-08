FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY sdk ./sdk
COPY rag_api ./rag_api

ENV PYTHONPATH=/app/sdk:/app
CMD ["sh", "-c", "uvicorn rag_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
