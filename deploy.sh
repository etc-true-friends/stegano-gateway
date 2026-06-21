#!/bin/bash
         set -e

         cd ~/stegano-gateway

         docker compose down --remove-orphans
         docker compose build --no-cache
         docker compose up -d

         docker ps