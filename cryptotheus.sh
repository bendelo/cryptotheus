#!/usr/bin/env bash

pushd "`dirname "$0"`" > /dev/null

if [ ! -d logs ]; then
  mkdir logs
fi

if [ -f "$HOME/.cryptotheus" ]; then
  source "$HOME/.cryptotheus"
fi

nohup python cryptotheus.py > logs/cryptotheus.log 2>&1 &

popd > /dev/null
