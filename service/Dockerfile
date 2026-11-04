FROM python:3.12-slim
WORKDIR /app
COPY service/requirements.txt /app/service/requirements.txt
RUN pip install --no-cache-dir -r /app/service/requirements.txt
COPY harness-bench /app/harness-bench
COPY service /app/service
ENV SERVICE_DATA_DIR=/data/som
EXPOSE 8000
# Single worker only: one serialized writer owns SQLite state + budget ledger.
CMD ["python", "-m", "uvicorn", "service.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
