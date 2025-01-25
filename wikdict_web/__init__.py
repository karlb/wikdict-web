import os
from subprocess import check_output

import jinja2
from flask import (
    Flask,
    Response,
    redirect,
    request,
    url_for,
    session,
    send_from_directory,
    abort,
)
import flask_assets
import markdown
from markupsafe import Markup

app = Flask(__name__.split(".")[0], static_folder="../static")
app.config.update(SECRET_KEY=os.environ.get("FLASK_SECRET"))
app.jinja_env.undefined = jinja2.StrictUndefined
assets = flask_assets.Environment(app)

import wikdict_web.lookup as lookup
import wikdict_web.reader
import wikdict_web.admin
import wikdict_web.base as base
import wikdict_web.typeahead

ADMINS = ["karl@karl.berlin"]
ASSET_REVISION = check_output(
    "git describe --abbrev=12 --always --dirty=+".split(" "), cwd=base.APP_ROOT
)


# simple cache busting for static files, since Flask-Assets is only usable for js, css, etc.
@app.url_defaults
def static_cache_buster(endpoint, values):
    if endpoint == "static":
        values["_v"] = ASSET_REVISION


app.debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
if not app.debug:
    import logging

    from logging.handlers import RotatingFileHandler

    file_handler = RotatingFileHandler(
        os.environ["DATA_ROOT"] + "/flask.log", maxBytes=10000, backupCount=1
    )
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    from logging.handlers import SMTPHandler

    credentials = (os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
    mail_handler = SMTPHandler(
        "smtp.sendgrid.net",
        "server-error@wikdict.com",
        ADMINS,
        "WikDict Error",
        credentials,
    )
    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler)

app.jinja_env.add_extension("jinja2.ext.loopcontrols")
#'jinja2.ext.autoescape',
#'jinja2.ext.with_',


@app.route("/")
def index():
    last_dict = session.get("last_dicts", ["de-en"])[0]
    from_lang, to_lang = last_dict.split("-")
    return lookup.lookup(from_lang, to_lang)
    # return redirect(url_for('lookup', from_lang=from_lang, to_lang=to_lang))


@app.route("/page/<page_name>")
def page(page_name):
    try:
        with open(
            base.APP_ROOT + "/markdown/" + page_name + ".md", encoding="utf-8"
        ) as f:
            content = f.read()
    except FileNotFoundError:
        abort(404)
    content = Markup(markdown.markdown(content))
    return base.render_template(
        "markdown.html",
        page_name=page_name,
        content=content,
    )


@app.route("/opensearch/<from_lang>-<to_lang>")
def opensearch(from_lang, to_lang):
    return Response(
        base.render_template(
            "opensearch.xml",
            from_lang=from_lang,
            to_lang=to_lang,
        ),
        mimetype="application/opensearchdescription+xml",
    )


@app.route("/robots.txt")
# @app.route('/sitemap.xml')  # just add additional routes for more static files in root
def static_from_root():
    return send_from_directory(app.static_folder + "/root", request.path[1:])
