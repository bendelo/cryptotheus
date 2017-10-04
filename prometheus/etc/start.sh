#!/bin/bash

if [ ! -d "$PROMETHEUS_HOME" ]; then

  echo '$PROMETHEUS_HOME not defined.'

  exit 1

fi

pushd "$PROMETHEUS_HOME" > /dev/null

if [ ! -d "logs" ]; then
  mkdir logs
fi

nohup ./prometheus \
	-storage.local.target-heap-size=536870912 \
	-web.listen-address=localhost:9090 \
	-web.enable-remote-shutdown=true \
	> logs/prometheus-start.log 2>&1 \
&

popd > /dev/null
