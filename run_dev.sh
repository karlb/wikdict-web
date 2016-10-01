#!/usr/bin/env bash
if [ ! -d venv ]; then
	virtualenv -p python3 venv
fi
if [ ! -d wsgi/lib ]; then
	python3 -c "`wget -qO- https://bitbucket.org/!api/2.0/snippets/karlb/j6gxM/8a09f53c78284c89b10658434f4d96528e14f351/files/make_sqlite_ext.py`" wsgi/lib spellfix
fi

. venv/bin/activate

set -o allexport
source development_env.sh
set +o allexport

pip install --quiet -r requirements.txt
if [[ $1 == test ]]; then
    python3 wsgi/web_tests.py
else
    python3 wsgi/runserver.py
fi
