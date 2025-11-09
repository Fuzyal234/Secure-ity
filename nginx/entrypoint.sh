#!/bin/sh
set -e

CERT_PATH=${SSL_CERT_PATH:-/etc/nginx/certs/cert.pem}
KEY_PATH=${SSL_KEY_PATH:-/etc/nginx/certs/key.pem}
CERT_DAYS=${SSL_CERT_DAYS:-365}
COMMON_NAME=${SSL_CERT_CN:-localhost}

if [ ! -f "$CERT_PATH" ] || [ ! -f "$KEY_PATH" ]; then
  echo "Generating self-signed TLS certificate for ${COMMON_NAME}"
  mkdir -p "$(dirname "$CERT_PATH")"
  openssl req -x509 -nodes -days "$CERT_DAYS" -newkey rsa:2048 \
    -keyout "$KEY_PATH" \
    -out "$CERT_PATH" \
    -subj "/CN=${COMMON_NAME}" \
    -addext "subjectAltName=DNS:${COMMON_NAME},IP:127.0.0.1" >/dev/null 2>&1
else
  echo "TLS certificate already present, skipping generation."
fi

