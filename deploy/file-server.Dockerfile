ARG NODE_RUNTIME=master-rcoder-base:latest
FROM ${NODE_RUNTIME}
USER root
WORKDIR /opt/singux-file-server
RUN npm install -g pnpm@10.27.0 --registry=https://registry.npmmirror.com
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile --prod --registry=https://registry.npmmirror.com
COPY src ./src
RUN mkdir -p /data/projects /data/dist /data/uploads /data/templates /data/logs /data/computer \
    && chown -R node:node /data /opt/singux-file-server
ENV NODE_ENV=production PORT=60000 \
    PROJECT_SOURCE_DIR=/data/projects DIST_TARGET_DIR=/data/dist \
    UPLOAD_PROJECT_DIR=/data/uploads INIT_PROJECT_DIR=/data/templates \
    LOG_BASE_DIR=/data/logs COMPUTER_WORKSPACE_DIR=/data/computer \
    COMPUTER_LOG_DIR=/data/logs/computer
USER node
EXPOSE 60000
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD node -e "fetch('http://127.0.0.1:60000/health').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"
ENTRYPOINT ["node", "src/server.js"]
