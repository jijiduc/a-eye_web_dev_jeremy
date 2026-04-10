#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CERT_DIR="$ROOT_DIR/local-certs"

mkdir -p "$CERT_DIR"

openssl req \
  -x509 \
  -nodes \
  -newkey rsa:2048 \
  -keyout "$CERT_DIR/aeye.local.key" \
  -out "$CERT_DIR/aeye.local.crt" \
  -days 365 \
  -subj "/CN=aeye.local" \
  -addext "subjectAltName=DNS:aeye.local,DNS:localhost,IP:127.0.0.1"

echo "Created:"
echo "  $CERT_DIR/aeye.local.crt"
echo "  $CERT_DIR/aeye.local.key"
echo
echo "Add this hosts entry if needed:"
echo "  127.0.0.1 aeye.local"
