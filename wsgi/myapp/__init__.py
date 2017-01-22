import os

from flask import Flask, Response, redirect, request, url_for, session, send_from_directory, Markup
import markdown

app = Flask(__name__.split('.')[0], static_folder='../static')

import myapp.lookup as lookup
import myapp.admin
import myapp.base as base

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
    return lookup.lookup(from_lang, to_lang)
    # return redirect(url_for('lookup', from_lang=from_lang, to_lang=to_lang))


@app.route('/page/<page_name>')
def page(page_name):
    with open(base.APP_ROOT + '/markdown/' + page_name + '.md', encoding="utf-8") as f:
        content = f.read()
    content = Markup(markdown.markdown(content))
    return base.render_template('markdown.html',
        page_name=page_name,
        content=content,
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


@app.route('/robots.txt')
#@app.route('/sitemap.xml')  # just add additional routes for more static files in root
def static_from_root():
    return send_from_directory(app.static_folder + '/root', request.path[1:])


if __name__ == "__main__":
    app.run()
