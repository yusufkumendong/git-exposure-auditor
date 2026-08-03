FROM debian:12-slim
RUN apt-get update && apt-get install -y --no-install-recommends bash ca-certificates curl jq python3 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . /app
RUN chmod +x /app/bin/gea /app/scripts/*.sh /app/tests/*.sh
ENTRYPOINT ["/app/bin/gea"]
CMD ["--help"]
