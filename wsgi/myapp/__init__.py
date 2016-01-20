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


@app.route('/admin/activity')
def show_activity():
    rows = base.db_query("logging", """
        SELECT strftime('%Y-W%W', ts) as week, count(*) AS queries,
            count(CASE WHEN results1+results2 > 0 THEN 1 END) AS with_result,
            round(avg(results1+results2), 1) AS avg_results
        FROM search_log
        WHERE user_agent NOT LIKE '%bot%'
        GROUP BY 1 ORDER BY 1 DESC
        LIMIT 30
    """, path='')
    return base.render_template('admin/activity.html', rows=rows)


@app.route('/admin/week/<week>')
def show_week(week):
    rows = base.db_query("logging", """
        SELECT *
        FROM search_log
        WHERE strftime('%Y-W%W', ts) = ?
          AND user_agent NOT LIKE '%bot%'
        ORDER BY 1
    """, [week], path='')
    return base.render_template('admin/activity.html', rows=rows)


@app.route('/admin/user_agents')
def show_user_agents():
    rows = base.db_query("logging", """
        SELECT user_agent,  count(*) AS count
        FROM search_log
        WHERE user_agent IS NOT NULL AND user_agent NOT LIKE '%bot%'
        GROUP BY 1 ORDER BY 2 DESC
        LIMIT 50
    """, path='')
    return base.render_template('admin/user_agents.html', rows=rows)


@app.route('/admin/summary')
def show_summary():
    langs = base.db_query("logging", """
        SELECT lang1, lang2, count(*) AS count
        FROM search_log
        WHERE user_agent NOT LIKE '%bot%'
        GROUP BY 1, 2 ORDER BY 3 DESC
        LIMIT 10
    """, path='')
    recent_searches = base.db_query("logging", """
        SELECT DISTINCT lang1, lang2, query, results1 + results2 AS results
        FROM search_log
        WHERE user_agent NOT LIKE '%bot%'
        ORDER BY ts DESC
        LIMIT 50
    """, path='')
    return base.render_template('admin/summary.html',
        langs=langs,
        recent_hits=[x for x in recent_searches if x.results > 0],
        recent_misses=[x for x in recent_searches if x.results == 0],
    )


if __name__ == "__main__":
    app.run()
