. venv/bin/activate
pip install --quiet -r requirements.txt
if [ ! -d wsgi/lib ]; then
	python3 -c "`wget -qO- https://bitbucket.org/\!api/2.0/snippets/karlb/j6gxM/5513c1bab236e00766c8765fddfc79d7702b3a1b/files/make_sqlite_ext.py`" wsgi/lib spellfix
fi
export FLASK_DEBUG=true
export OPENSHIFT_LOG_DIR=.
export OPENSHIFT_SECRET_TOKEN='insecure-token-for-local-dev'
export OPENSHIFT_DATA_DIR='data'
python3 wsgi/runserver.py
