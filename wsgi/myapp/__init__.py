import os

from flask import Flask, Response, redirect, request, url_for, session

app = Flask(__name__.split('.')[0], static_folder='../static')

import myapp.lookup
from . import base

ADMINS = ['karl42@gmail.com']

app.debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
if not app.debug:
    import logging

    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        os.environ['OPENSHIFT_LOG_DIR'] + '/flask.log',
        maxBytes=10000, backupCount=1)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    from logging.handlers import SMTPHandler
    credentials = (os.environ.get('SENDGRID_USER'),
                   os.environ.get('SENDGRID_PASSWORD'))
    mail_handler = SMTPHandler('smtp.sendgrid.net',
                               'server-error@wikdict.com',
                               ADMINS, 'WikDict Error',
                               credentials)
    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler)

app.secret_key = os.environ['OPENSHIFT_SECRET_TOKEN']
app.jinja_env.add_extension('jinja2.ext.loopcontrols')
    #'jinja2.ext.autoescape',
    #'jinja2.ext.with_',


@app.route('/')
def index():
    last_dict = session.get('last_dicts', ['de-en'])[0]
    from_lang, to_lang = last_dict.split('-')
    return redirect(url_for('lookup', from_lang=from_lang, to_lang=to_lang))


@app.route('/page/<page_name>')
def page(page_name):
    return base.render_template(page_name + '.html',
        page_name=page_name,
    )


@app.route('/opensearch/<from_lang>-<to_lang>')
def opensearch(from_lang, to_lang):
    return Response(
        base.render_template('opensearch.xml',
            from_lang=from_lang,
            to_lang=to_lang,
        ),
        mimetype='application/opensearchdescription+xml',
    )


if __name__ == "__main__":
    app.run()
