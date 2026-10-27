FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends unixodbc libodbc2 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
COPY config ./config
RUN pip install --no-cache-dir '.[odbc,azure]' \
    && useradd --create-home --uid 10001 pipeline \
    && mkdir /data && chown pipeline:pipeline /data
# IT must supply the approved Linux Unanet/Data Virtuality driver and DSN.
# unixODBC above is the driver manager; it is NOT the vendor's source driver.
USER pipeline
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "-m", "unanet_pipeline.refresh"]
CMD ["--odbc", "--output-dir", "/data", "--publish"]
