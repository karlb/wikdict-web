import os
import sqlite3

from flask import Flask, render_template, redirect, request, url_for, flash

from .languages import language_names
from . import app


DATA_DIR = os.environ['OPENSHIFT_DATA_DIR']


@app.route('/<from_lang>-<to_lang>/')
@app.route('/<from_lang>-<to_lang>/<query>')
def loopup(from_lang, to_lang, query=None):
    results = search_query(from_lang, to_lang, query)
    return render_template('lookup.html',
        language_names=language_names,
        from_lang='de',
        to_lang='fr',
        query=query,
        results=[results],
    )


def search_query(from_lang, to_lang, search_term, **kwargs):
    conn = sqlite3.connect(DATA_DIR + '/{}-{}.sqlite3'.format(from_lang, to_lang))
    conn.row_factory = sqlite3.Row
    cur = conn.execute("""
                SELECT lexentry, written_rep, part_of_speech, sense_list, trans_list
                FROM (
                        SELECT DISTINCT lexentry
                        FROM search_trans
                        WHERE form MATCH ?
                     )
                     JOIN translation USING (lexentry)
                UNION ALL
                SELECT NULL, written_rep, NULL, NULL, trans_list
                FROM search_reverse_trans
                WHERE written_rep MATCH ?
            """, [search_term, search_term])
    results = list(cur)
    for r in results:
        print(dict(r))
    return results


def vocable_details(vocable, lang, part_of_speech):
    conn = sqlite3.connect(DATA_DIR + '/{}.sqlite3'.format(lang))
    conn.row_factory = sqlite3.Row
    cur = conn.execute("""
                SELECT CASE WHEN count(*) = 1 THEN gender END AS gender,
                       group_concat(pronun_list, ' | ') AS pronun_list
                FROM entry
                WHERE written_rep = ?
                  AND (? IS NULL OR part_of_speech = ?);
            """, [vocable, part_of_speech, part_of_speech])
    r = list(cur)[0]
    print(dict(r))
    return {
        'gender': r['gender'],
        'pronuns': set(r['pronun_list'].split(' | ')) if r['pronun_list'] else None
    }


@app.context_processor
def add_fucntions():
    return dict(vocable_details=vocable_details)
