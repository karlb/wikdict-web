#import sqlite3
import apsw
import urllib.parse

from flask import Flask, render_template, redirect, request, url_for, flash, g

from .languages import language_names
from . import app
from . import base
from .base import DATA_DIR, timing


@app.route('/<from_lang>-<to_lang>/')
@app.route('/<from_lang>-<to_lang>/<query>')
def lookup(from_lang, to_lang, query=None):
    if [from_lang, to_lang] != sorted((from_lang, to_lang)):
        return redirect(url_for('lookup', from_lang=to_lang, to_lang=from_lang,
                                          query=query))
    if query:
        results = [
            search_query(from_lang, to_lang, query),
            search_query(to_lang, from_lang, query),
        ]
    else:
        results = None
    return base.render_template('lookup.html',
        from_lang=from_lang,
        to_lang=to_lang,
        query=query,
        results=results,
        page_name='lookup',
    )

@app.route('/lookup')
def lookup_redirect():
    url = '{}/{}'.format(request.args['index_name'], request.args['query'])
    return redirect(url)


@timing
def search_query(from_lang, to_lang, search_term, **kwargs):
    cur = apsw.Connection(DATA_DIR + '/{}-{}.sqlite3'.format(from_lang, to_lang)).cursor()
    cur.execute("""
                SELECT *
                FROM (
                    SELECT lexentry, written_rep, part_of_speech, sense_list, min_sense_num, trans_list
                    FROM (
                            SELECT DISTINCT lexentry
                            FROM search_trans
                            WHERE form MATCH ?
                        )
                        JOIN translation USING (lexentry)
                    UNION ALL
                    SELECT NULL, written_rep, NULL, NULL, NULL, trans_list
                    FROM search_reverse_trans
                    WHERE written_rep MATCH ?
                )
                ORDER BY length(written_rep), coalesce(min_sense_num, '99')
            """, [search_term, search_term])
    results = [dict(zip((d[0] for d in cur.getdescription()), row)) for row in cur]
    return results


@timing
def vocable_details(vocable, lang, part_of_speech):
    cur = apsw.Connection(DATA_DIR + '/{}.sqlite3'.format(lang)).cursor()
    cur.execute("""
            WITH matches AS (
                SELECT *
                FROM entry
                WHERE written_rep = ?
                    AND (? IS NULL OR part_of_speech = ?)
            )
            SELECT
                (
                    SELECT gender
                    FROM matches
                    GROUP BY 1
                    HAVING count(DISTINCT gender) = 1
                ) AS gender,
                (
                    SELECT pronun_list
                    FROM (SELECT * FROM matches ORDER BY lexentry LIMIT 1)
                ) AS pronun_list,
                (
                    SELECT display
                    FROM matches
                    GROUP BY 1
                    HAVING count(DISTINCT display) = 1
                ) AS display,
                (
                    SELECT display_addition
                    FROM matches
                    GROUP BY 1
                    HAVING count(DISTINCT display_addition) = 1
                ) AS display_addition,
                (SELECT count(*) FROM matches) AS count
        """, [vocable, part_of_speech, part_of_speech])
    r = dict(zip((d[0] for d in cur.getdescription()), cur.fetchone()))
    print(repr(r))
    return {
        'gender': r['gender'],
        'pronuns': set(r['pronun_list'].split(' | ')) if r['pronun_list'] else None,
        'wiktionary_url': None if r['count'] == 0 else vocable_link(vocable, lang),
        'display': r['display'] or vocable,
        'display_addition': r['display_addition'],
    }


def vocable_link(word, lang):
    wiki_name = word.replace(' ', '_')
    url = 'http://%s.wiktionary.org/wiki/%s#%s'
    lang_name = urllib.parse.quote_plus(language_names[lang]).replace('%', '.')
    return url % (lang, wiki_name, lang_name)


@app.context_processor
def add_fucntions():
    return dict(vocable_details=vocable_details)
