#!/bin/bash
set -e

cd ~/stegano-gateway

docker compose down --remove-orphans
docker compose pull
docker compose build --no-cache api-gateway
docker compose up -d

docker ps
