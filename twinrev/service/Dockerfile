# Build from the twinrev/ folder:  docker build -f service/Dockerfile -t openaiflex/twinrev-scenarios:0.1 .
# No household data goes into the image: the Austin files are mounted at /data/austin (see k8s.yaml).
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir numpy pandas fastapi "uvicorn[standard]" sqlalchemy psycopg2-binary
COPY service/*.py service/lv_lines.json ./
ENV PYTHONPATH=/app AUSTIN_DATA_DIR=/data/austin INFLUX_URL=http://influxdb.sogno:8086 INFLUX_DB=openaiflex \
    TWINREV_URL=http://dt-backend-service.digital-twin:8000
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
