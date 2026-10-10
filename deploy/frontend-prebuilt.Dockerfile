FROM singux/frontend:1.1.10-20260929-background
COPY dist/ /usr/share/nginx/html/
COPY k8s/default.conf.template /etc/nginx/templates/default.conf.template
LABEL org.opencontainers.image.version="1.1.10-20261008-tenant-admin"
