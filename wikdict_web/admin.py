import os
from functools import wraps

from flask import request, Response

from . import app
from . import base


def check_auth(username, password):
    return (username == 'admin' and
            password == os.environ['WIKDICT_ADMIN_PASSWORD'])


def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


@app.route('/admin/')
@requires_auth
def admin_index():
    base.db_query('logging', """
        CREATE VIEW IF NOT EXISTS search_log_filtered AS
        SELECT * FROM search_log
        WHERE NOT hidden
        AND user_agent NOT LIKE '%bot%' AND user_agent NOT LIKE '%Yahoo! Slurp%';
    """, path='')
    return base.render_template('admin/index.html', urls=[
        rule.endpoint
        for rule in app.url_map.iter_rules()
        if not rule.arguments and rule.endpoint != 'admin_index'
    ])


@app.route('/admin/activity')
@requires_auth
def show_activity():
    rows = base.db_query("logging", """
        SELECT strftime('%Y-W%W', ts) as week, count(*) AS queries,
            count(CASE WHEN results1+results2 > 0 THEN 1 END) AS with_result,
            round(avg(results1+results2), 1) AS avg_results
        FROM search_log_filtered
        GROUP BY 1 ORDER BY 1 DESC
        LIMIT 30
    """, path='')
    return base.render_template('admin/activity.html', rows=rows)


@app.route('/admin/week/<week>')
@requires_auth
def show_week(week):
    rows = base.db_query("logging", """
        SELECT *
        FROM search_log_filtered
        WHERE strftime('%Y-W%W', ts) = ?
        ORDER BY 1
    """, [week], path='')
    return base.render_template('admin/activity.html', rows=rows)


@app.route('/admin/user_agents')
@requires_auth
def show_user_agents():
    rows = base.db_query("logging", """
        SELECT user_agent,  count(*) AS count
        FROM search_log_filtered
        GROUP BY 1 ORDER BY 2 DESC
        LIMIT 50
    """, path='')
    return base.render_template('admin/user_agents.html', rows=rows)


@app.route('/admin/summary')
@requires_auth
def show_summary():
    langs = base.db_query("logging", """
        SELECT lang1, lang2, count(*) AS count
        FROM search_log_filtered
        GROUP BY 1, 2 ORDER BY 3 DESC
        LIMIT 10
    """, path='')
    recent_searches = base.db_query("logging", """
        SELECT DISTINCT lang1, lang2, query, results1 + results2 AS results
        FROM search_log_filtered
        ORDER BY ts DESC
        LIMIT 50
    """, path='')
    return base.render_template('admin/summary.html',
                                langs=langs,
                                recent_hits=[x for x in recent_searches if x.results > 0],
                                recent_misses=[x for x in recent_searches if x.results == 0],
                                )
