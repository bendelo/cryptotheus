#!/bin/bash

if [ ! -d "$PROMETHEUS_HOME" ]; then

  echo '$PROMETHEUS_HOME not defined.'

  exit 1

fi

pushd "$PROMETHEUS_HOME" > /dev/null

if [ ! -d "logs" ]; then
  mkdir logs
fi

if [ -f "logs/data.tar" ]; then
  rm "logs/data.tar"
fi

if [ -f "logs/data.tar.gz" ]; then
  rm "logs/data.tar.gz"
fi

tar cf "logs/data.tar" "data" && gzip --best "logs/data.tar"

popd > /dev/null
