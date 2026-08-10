FROM debian:12-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends bash ca-certificates curl python3 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . /app
RUN chmod +x /app/bin/gea /app/scripts/*.sh /app/tests/*.sh /app/tests/unit.py \
    && python3 -m py_compile /app/gea/*.py
ENTRYPOINT ["/app/bin/gea"]
CMD ["--help"]
