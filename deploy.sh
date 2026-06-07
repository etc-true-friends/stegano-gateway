#!/bin/bash
set -e

cd ~/stegano-gateway

git fetch origin
git checkout main
git reset --hard origin/main

docker compose down
docker compose build --no-cache
docker compose up -d

docker ps