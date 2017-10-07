#!/usr/bin/env bash

FPID="$GRAFANA_HOME/logs/grafana.pid"

if [ ! -f "$FPID" ]; then
  echo "[ERROR] PID file not found : $FPID"
  exit 1
fi

GPID="`cat "$FPID"`"

kill "$GPID"

if [ $? -ne 0 ]; then
  echo "[ERROR] Failed to stop instance : $GPID"
  exit 1
fi

echo "[INFO] Stopped instance : $GPID"
rm "$FPID"
