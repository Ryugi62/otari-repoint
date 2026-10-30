#!/bin/sh
# 스모크용 게이트웨이 기동 (공식 이미지 mzdotai/otari). 정리: docker rm -f otari sandbox; docker network rm otari-smoke
cd "$(dirname "$0")"
docker rm -f otari >/dev/null 2>&1
docker run -d --rm --name otari --network otari-smoke --add-host host.docker.internal:host-gateway -p 127.0.0.1:8000:8000 \
 -e OTARI_PROVIDER_ACCOUNT_PEPPER=$(openssl rand -base64 32) -v "$PWD/config.smoke.yml:/app/config.yml:ro" mzdotai/otari:latest otari serve --config /app/config.yml
