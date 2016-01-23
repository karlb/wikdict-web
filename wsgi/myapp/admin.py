from . import app
from . import base


@app.route('/admin/')
def admin_index():
    return base.render_template('admin/index.html', urls=[
        rule.endpoint
        for rule in app.url_map.iter_rules()
        if not rule.arguments and rule.endpoint != 'admin_index'
    ])


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
