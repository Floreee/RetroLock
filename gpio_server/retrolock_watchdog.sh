#!/bin/bash

TOKEN_FILE="/etc/retrolock/token"

if [[ ! -f "$TOKEN_FILE" ]]; then
  echo "$(date): Token file not found at $TOKEN_FILE"
  exit 1
fi

TOKEN=$(cat "$TOKEN_FILE")

while true; do
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5001/status)
  
  if [[ "$HTTP_CODE" != "200" ]]; then
    echo "$(date): Retrolock not responding properly (HTTP $HTTP_CODE), restarting..."
    systemctl restart retrolock.service
  fi
  
  sleep 30
done

