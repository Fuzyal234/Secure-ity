FROM nginx:1.25-alpine

RUN apk add --no-cache openssl

COPY nginx.conf /etc/nginx/nginx.conf
COPY entrypoint.sh /docker-entrypoint.d/10-generate-cert.sh

RUN chmod +x /docker-entrypoint.d/10-generate-cert.sh \
    && mkdir -p /etc/nginx/certs

