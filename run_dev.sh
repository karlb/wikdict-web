#!/usr/bin/env bash

set -o allexport
source development_env.sh
set +o allexport

if [[ $1 == test ]]; then
    uv run python -m unittest tests/web_tests.py
else
    uv run python -m wikdict_web
fi
