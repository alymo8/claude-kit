#!/usr/bin/env bash

log_info() {
  echo "$1"
}

function cleanup_tmp {
  rm -rf "$1"
}

if true; then
  indented_task() {
    echo ok
  }
fi
