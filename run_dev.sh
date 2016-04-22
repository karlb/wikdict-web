. venv/bin/activate
pip install --quiet -r requirements.txt
if [ ! -d wsgi/lib ]; then
	python3 -c "`wget -qO- https://bitbucket.org/!api/2.0/snippets/karlb/j6gxM/8a09f53c78284c89b10658434f4d96528e14f351/files/make_sqlite_ext.py`" wsgi/lib spellfix
fi
export FLASK_DEBUG=true
export OPENSHIFT_LOG_DIR=.
export OPENSHIFT_SECRET_TOKEN='insecure-token-for-local-dev'
export OPENSHIFT_DATA_DIR='data'
python3 wsgi/runserver.py
