#!/bin/sh
# Local/CI smoke test for the actual images. No Azure or database credentials.
set -eu
cd "$(dirname "$0")/.."
name="lz-image-check-$$"
cleanup() {
  docker rm -f "$name-web" "$name-api" >/dev/null 2>&1 || true
  docker network rm "$name" >/dev/null 2>&1 || true
  docker image rm "$name-api" "$name-web" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM
docker build -t "$name-api" apps/api
docker build -t "$name-web" apps/frontend
docker network create "$name" >/dev/null
docker run -d --name "$name-api" --network "$name" --network-alias api -e USE_IN_MEMORY=true -e EVENTS_ENABLED=false "$name-api" >/dev/null
docker run -d --name "$name-web" --network "$name" -p 127.0.0.1::8080 -e API_PLATFORM_ORIGIN=http://api:8000 -e API_TENANT_ORIGIN=http://api:8000 -e API_ACTIVITIES_ORIGIN=http://api:8000 "$name-web" >/dev/null
port=$(docker inspect --format '{{(index (index .NetworkSettings.Ports "8080/tcp") 0).HostPort}}' "$name-web")
base="http://127.0.0.1:$port"
attempt=0
until curl -fsS "$base/healthz" > /dev/null; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 30 ]; then
    docker logs "$name-web"
    docker logs "$name-api"
    exit 1
  fi
  sleep 1
done
curl -fsS "$base/healthz" >/dev/null
curl -fsS "$base/" | python3 -c 'import sys; assert "<html" in sys.stdin.read().lower()'
status=$(curl -sS -o /dev/null -w '%{http_code}' "$base/api/tenant/requests")
[ "$status" = 401 ]
printf '%s\n' 'Nginx → API: imágenes reales y salud correctas. La API de datos rechaza acceso anónimo (401).'
