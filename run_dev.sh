#!/usr/bin/env bash
if [ ! -d venv ]; then
	python3 -m venv venv
fi

. venv/bin/activate

set -o allexport
source development_env.sh
set +o allexport

pip install --quiet -r requirements.txt
if [[ $1 == test ]]; then
    python3 -m unittest tests/web_tests.py
else
    python3 -m wikdict_web
fi
