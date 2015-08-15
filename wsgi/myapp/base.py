import os
from collections import OrderedDict, namedtuple

import flask
from flask import session
import apsw

from .languages import language_names

DATA_DIR = os.environ['OPENSHIFT_DATA_DIR']


def get_lang_pairs():
    cur = apsw.Connection(DATA_DIR + '/wikdict.sqlite3').cursor()
    cur.execute("""
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
    results = [dict(zip((d[0] for d in cur.getdescription()), row)) for row in cur]
    return results


def db_query(db_name, stmt):
    cur = apsw.Connection(DATA_DIR + '/' + db_name + '.sqlite3').cursor()
    cur.execute(stmt)
    Row = namedtuple('Row', (d[0] for d in cur.getdescription()))
    results = [Row(*r) for r in cur]
    print(results)
    return results


def render_template(filename, **kwargs):
    if 'from_lang' in kwargs:
        session.setdefault('last_dicts', []).insert(0, kwargs['from_lang'] + '-' + kwargs['to_lang'])
        # remove duplicates
        session['last_dicts'] = list(OrderedDict.fromkeys(session['last_dicts']))

    return flask.render_template(filename,
        language_names=language_names,
        available_langs=[
            row.from_lang for row in db_query('wikdict',
                                              "SELECT from_lang FROM lang_pair GROUP BY from_lang ORDER BY sum(translations) DESC")
        ],
        lang_pairs=get_lang_pairs(),
        last_dicts=[d for d in session.get('last_dicts', []) if d != kwargs['from_lang'] + '-' + kwargs['to_lang']],
        **kwargs)
