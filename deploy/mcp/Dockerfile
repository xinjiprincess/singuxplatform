# Local compatibility build; base runtime is recorded in sources.json.
ARG MCP_RUNTIME=singux-mcp-proxy:latest
FROM ${MCP_RUNTIME}
USER root
COPY mcp-v0.2.8.tar.xz /tmp/mcp-v0.2.8.tar.xz
RUN echo '80fbada7d6fb4a2c7802fc73a0920dab19c3541459b292304c14a32044be0fb5  /tmp/mcp-v0.2.8.tar.xz' | sha256sum -c - \
    && tar -xJf /tmp/mcp-v0.2.8.tar.xz -C /tmp \
    && install -m 755 /tmp/mcp-stdio-proxy-x86_64-unknown-linux-gnu/mcp-proxy /app/mcp-proxy \
    && install -m 755 /root/.local/bin/uv /usr/local/bin/uv \
    && ln -sf /usr/local/bin/uv /usr/local/bin/uvx \
    && mkdir -p /home/mcp /app/logs \
    && chown -R 10001:10001 /home/mcp /app/logs \
    && rm -rf /tmp/mcp-stdio-proxy-x86_64-unknown-linux-gnu /tmp/mcp-v0.2.8.tar.xz
COPY config.yml /app/config.yml
ENV HOME=/home/mcp RUST_LOG=warn NPM_CONFIG_REGISTRY=https://registry.npmmirror.com UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple
WORKDIR /app
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 CMD curl -fsS http://127.0.0.1:8080/health || exit 1
ENTRYPOINT ["/app/mcp-proxy"]
