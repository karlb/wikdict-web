. venv/bin/activate
pip install --quiet -r requirements.txt
export FLASK_DEBUG=true
export OPENSHIFT_LOG_DIR=.
export OPENSHIFT_SECRET_TOKEN='insecure-token-for-local-dev'
python3 wsgi/runserver.py
