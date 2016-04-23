#import sqlite3
import urllib.parse

from flask import Flask, render_template, redirect, request, url_for, flash, g

from .languages import language_names
from . import app
from . import base
from .base import timing, db_query


@app.route('/<from_lang>-<to_lang>/')
@app.route('/<from_lang>-<to_lang>/<query>')
def lookup(from_lang, to_lang, query=None):
    if [from_lang, to_lang] != sorted((from_lang, to_lang)):
        return redirect(url_for('lookup', from_lang=to_lang, to_lang=from_lang,
                                          query=query))

    templ_vals = {}

    if query:
        results = [
            search_query(from_lang, to_lang, query),
            search_query(to_lang, from_lang, query),
        ]
        if not results[0] and not results[1]:
            templ_vals['did_you_mean'] = spellfix(from_lang, to_lang, query)

        # log results for later analysis
        db_query('logging', """
            CREATE TABLE IF NOT EXISTS search_log (
                ts timestamp DEFAULT current_timestamp, lang1 text, lang2 text,
                query text, results1, results2, ip, referrer, user_agent);
        """, path='')
        if request.headers.getlist("X-Forwarded-For"):
            ip = request.headers.getlist("X-Forwarded-For")[0]
        else:
            ip = request.remote_addr
        db_query('logging', """
                INSERT INTO search_log (lang1, lang2, query,
                                        results1, results2,
                                        ip, referrer, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [from_lang, to_lang, query, len(results[0]), len(results[1]),
             ip, request.referrer, request.user_agent.string],
            path='')
    else:
        results = None
    return base.render_template('lookup.html',
        from_lang=from_lang,
        to_lang=to_lang,
        query=query,
        results=results,
        page_name='lookup',
        **templ_vals
    )

@app.route('/lookup')
def lookup_redirect():
    url = '{}/{}'.format(request.args['index_name'], request.args['query'])
    return redirect(url)


@timing
def search_query(from_lang, to_lang, search_term, **kwargs):
    return db_query(from_lang + '-' + to_lang, """
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
                LIMIT 100
            )
            ORDER BY length(written_rep), coalesce(min_sense_num, '99')
        """, [search_term, search_term])


@timing
def spellfix(from_lang, to_lang, search_term):
    translated_fixes = db_query(from_lang + '-' + to_lang, """
            SELECT word
            FROM (
                SELECT DISTINCT word, score
                FROM spellfix_entry
                    JOIN translation ON (written_rep = word)
                WHERE word MATCH ?
                  AND scope=1
                  AND distance <= 100
                  AND top=50
                UNION ALL
                SELECT DISTINCT word, score
                FROM other_lang.spellfix_entry
                    JOIN other_pair.translation ON (written_rep = word)
                WHERE word MATCH ?
                  AND scope=1
                  AND distance <= 100
                  AND top=50
            )
            WHERE lower(word) != lower(?)
            ORDER BY score LIMIT 3;
        """,
        [search_term, search_term, search_term],
        attach_dbs=dict(
            lang=from_lang,
            other_lang=to_lang,
            other_pair=to_lang + '-' + from_lang
        )
    )
    return [r.word for r in translated_fixes]


@timing
def vocable_details(vocable, lang, part_of_speech):
    r = db_query(lang, """
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
        """, [vocable, part_of_speech, part_of_speech])[0]
    return {
        'gender': r.gender,
        'pronuns': set(r.pronun_list.split(' | ')) if r.pronun_list else None,
        'wiktionary_url': None if r.count == 0 else vocable_link(vocable, lang),
        'display': r.display or vocable,
        'display_addition': r.display_addition,
    }


def entry_details(lexentry, lang):
    rows = db_query(lang, """
        SELECT *
        FROM entry
        WHERE lexentry = ?
    """, [lexentry])
    if not rows:
        # this should not happen, but for unknown reasons, it did happen for eng/do_you_speak_something__Phrase__1
        # when searching for 'do'
        return {}
    r = rows[0]._asdict()
    r.update({
        'display': r['display'] or r['written_rep'],
        'display_addition': r['display_addition'],
        'wiktionary_url': vocable_link(r['written_rep'], lang),
    })
    return r


def vocable_link(word, lang):
    wiki_name = word.replace(' ', '_')
    url = 'http://%s.wiktionary.org/wiki/%s#%s'
    lang_name = urllib.parse.quote_plus(language_names[lang]).replace('%', '.')
    return url % (lang, wiki_name, lang_name)


@app.context_processor
def add_functions():
    return dict(
        vocable_details=vocable_details,
        entry_details=entry_details,
    )
