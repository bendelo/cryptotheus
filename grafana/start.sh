#!/usr/bin/env bash

if [ ! -d "$GRAFANA_HOME" ]; then
  echo '[ERROR] GRAFANA_HOME not defined.'
  exit 1
fi

pushd "$GRAFANA_HOME" > /dev/null

if [ ! -d "logs" ]; then
  mkdir "logs"
fi

nohup \
  ./bin/grafana-server \
  -pidfile "logs/grafana.pid" \
> "logs/grafana.log" 2>&1 &

popd > /dev/null
