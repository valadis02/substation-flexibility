# Build from the flexibility/ folder:  docker build -f service/Dockerfile -t openaiflex/flex-envelope:0.1 .
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir numpy pandas scikit-learn fastapi "uvicorn[standard]"
COPY flexsub ./flexsub
COPY data/processed ./data/processed
COPY data/splits.json ./data/splits.json
COPY service/*.py ./
ENV PYTHONPATH=/app INFLUX_URL=http://influxdb.sogno:8086 INFLUX_DB=openaiflex DATA_DIR=/app/data
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
