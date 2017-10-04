#!/usr/bin/env bash

pushd "`dirname "$0"`" > /dev/null

if [ ! -d logs ]; then
  mkdir logs
fi

nohup python cryptotheus/ticker.py > logs/ticker.log 2>&1 &

popd > /dev/null
