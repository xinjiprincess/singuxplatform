ARG RCODER_BUILD_IMAGE=singux/rcoder:20260929-build
FROM ${RCODER_BUILD_IMAGE}
# Windows checkouts may contain CRLF; normalize only the container scripts.
RUN sed -i 's/\r$//' /app/agent-runner-start.sh /usr/local/bin/start-ttyd.sh \
    && bash -n /app/agent-runner-start.sh \
    && bash -n /usr/local/bin/start-ttyd.sh
CMD ["/app/bin/rcoder"]
