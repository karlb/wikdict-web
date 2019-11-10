#!/usr/bin/env bash
if [ ! -d venv ]; then
	python3 -m venv venv
	CFLAGS='-DSQLITE_ENABLE_ICU' CPPFLAGS=`pkg-config --cflags icu-uc icu-uc icu-i18n` LDFLAGS=`pkg-config --libs icu-uc icu-uc icu-i18n` venv/bin/pip install git+git://github.com/karlb/pysqlite3
    python3 -c "`wget -qO- https://bitbucket.org/!api/2.0/snippets/karlb/j6gxM/38eff66f830e1c96b99e2ebb1312cae13c772c34/files/make_sqlite_ext.py`" wsgi/lib spellfix
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
