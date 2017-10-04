#!/bin/bash

if [ ! -d "$PROMETHEUS_HOME" ]; then

  echo '$PROMETHEUS_HOME not defined.'

  exit 1

fi

pushd "$PROMETHEUS_HOME" > /dev/null

if [ ! -d "logs" ]; then
  mkdir logs
fi

curl -s -X POST "http://localhost:9090/-/reload" > logs/prometheus-reload.log 2>&1

popd > /dev/null
