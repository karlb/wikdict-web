import os
import time
import functools
from collections import OrderedDict, namedtuple

import apsw
import flask
from flask import session, g

from .languages import language_names

DATA_DIR = os.environ['OPENSHIFT_DATA_DIR']


def timing(f):
    @functools.wraps(f)
    def f_with_timing(*args, **kwargs):
        start = time.time()
        result = f(*args, **kwargs)
        duration = time.time() - start
        g.timing = getattr(g, 'timing', {})
        g.timing[f.__name__] = g.timing.get(f.__name__, 0) + duration
        return result
    return f_with_timing


@timing
def get_lang_pairs():
    return db_query('wikdict', """
        SELECT from_lang, to_lang, sum(total_trans) AS total_trans
        FROM (
            SELECT from_lang, to_lang, translations + reverse_translations AS total_trans
            FROM lang_pair
            UNION ALL
            SELECT to_lang, from_lang, translations + reverse_translations AS total_trans
            FROM lang_pair
        )
        WHERE from_lang < to_lang
        GROUP BY from_lang, to_lang
        ORDER BY sum(total_trans) DESC
    """)


def db_query(db_name, stmt, bind_params=None, path='dict', attach_dbs=None, explain=False):
    path_for_db = lambda db: DATA_DIR + '/' + path + '/' + db + '.sqlite3'
    conn = apsw.Connection(path_for_db(db_name))
    conn.enableloadextension(True)
    conn.loadextension('/Users/karl/gdrive/code/gen_dict/download-sqlite/lib/spellfix1')
    cur = conn.cursor()
    for name, db in (attach_dbs or {}).items():
        cur.execute("ATTACH DATABASE '{}' AS {}".format(path_for_db(db), name))
    if explain:
        print('\nPlan for {}'.format(repr(stmt[:80])))
        cur.execute("EXPLAIN QUERY PLAN " + stmt, bind_params)
        for r in cur:
            print('\t' * r[1], r[3])
    cur.execute(stmt, bind_params)
    #print(stmt, bind_params)
    try:
        Row = namedtuple('Row', (d[0] for d in cur.getdescription()))
    except apsw.ExecutionCompleteError:
        return []
    return [Row(*r) for r in cur]


def render_template(filename, **kwargs):
    if 'from_lang' in kwargs:
        session.setdefault('last_dicts', []).insert(0, kwargs['from_lang'] + '-' + kwargs['to_lang'])
        # remove duplicates
        session['last_dicts'] = list(OrderedDict.fromkeys(session['last_dicts']))
    else:
        last_dict = session.get('last_dicts', ['de-en'])[0]
        kwargs['from_lang'], kwargs['to_lang'] = last_dict.split('-')

    return flask.render_template(filename,
        language_names=language_names,
        available_langs=[
            row.from_lang for row in db_query('wikdict',
                                              "SELECT from_lang FROM lang_pair GROUP BY from_lang ORDER BY sum(translations) DESC")
        ],
        lang_pairs=get_lang_pairs(),
        last_dicts=[d for d in session.get('last_dicts', []) if d != kwargs['from_lang'] + '-' + kwargs['to_lang']],
        **kwargs)
