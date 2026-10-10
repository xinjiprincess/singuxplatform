FROM singux/rcoder:20260929-local
USER root
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g; s|security.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       xvfb x11vnc openbox novnc websockify dbus-x11 x11-utils fonts-wqy-zenhei \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /home/user /app/logs \
    && ln -s /app/bin/agent_runner /usr/local/bin/agent_runner
ENV HOME=/home/user DISPLAY=:1 PROJECT_WORKSPACE_BASE=/home/user
COPY start.sh /app/start-computer.sh
RUN sed -i 's/\r$//' /app/start-computer.sh && chmod 755 /app/start-computer.sh && bash -n /app/start-computer.sh
EXPOSE 8086 50051 6080
HEALTHCHECK --interval=15s --start-period=30s --timeout=5s CMD curl -fsS http://127.0.0.1:8086/health && curl -fsS http://127.0.0.1:6080/vnc.html || exit 1
ENTRYPOINT ["/app/start-computer.sh"]
