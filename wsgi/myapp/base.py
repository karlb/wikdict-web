import os
import time
import functools
from collections import OrderedDict, namedtuple

import sqlite3
import flask
from flask import session, g

from .languages import language_names

DATA_DIR = os.environ['OPENSHIFT_DATA_DIR']
APP_ROOT = os.path.dirname(os.path.abspath(__file__))


def timing(f):
    @functools.wraps(f)
    def f_with_timing(*args, **kwargs):
        start = time.time()
        result = f(*args, **kwargs)
        duration = time.time() - start
        g.timing = getattr(g, 'timing', {})
        timing_dict = g.timing.setdefault(f.__name__, {
            'total_time': 0,
            'max_time': 0,
            'num_calls': 0,
        })
        timing_dict['total_time'] += duration
        timing_dict['num_calls'] += 1
        if duration > timing_dict['max_time']:
            timing_dict['max_time'] = duration
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


def namedtuple_factory(cursor, row):
    """
    Usage:
    con.row_factory = namedtuple_factory
    """
    fields = [col[0] + '_' if col[0] in ('from', ) else col[0]
              for col in cursor.description]
    Row = namedtuple("Row", fields)
    return Row(*row)


def db_query(db_name, stmt, bind_params=(), path='dict', attach_dbs=None, explain=False):
    path_for_db = lambda db: DATA_DIR + '/' + path + '/' + db + '.sqlite3'
    conn = sqlite3.connect(path_for_db(db_name))
    conn.isolation_level = None  # autocommit
    conn.row_factory = namedtuple_factory
    conn.enable_load_extension(True)
    conn.load_extension(APP_ROOT + '/../lib/spellfix1')
    cur = conn.cursor()
    for name, db in (attach_dbs or {}).items():
        cur.execute("ATTACH DATABASE '{}' AS {}".format(path_for_db(db), name))
    if explain:
        condensed_stmt = ' '.join(stmt.split())
        print('\nPlan for {}'.format(repr(condensed_stmt[:160])))
        cur.execute("EXPLAIN QUERY PLAN " + stmt, bind_params)
        for r in cur:
            print('\t' * r[1], r[3])
    cur.execute(stmt, bind_params)
    return list(cur)


def sorted_timing():
    return OrderedDict(sorted(g.timing.items(), key=lambda x: -x[1]['total_time']))


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
        sorted_timing=sorted_timing,
        **kwargs)
