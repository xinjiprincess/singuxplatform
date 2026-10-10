ARG FRONTEND_IMAGE=singux/frontend:1.1.10-20260929-portal
FROM ${FRONTEND_IMAGE}
COPY k8s/default.conf.template /etc/nginx/templates/default.conf.template
