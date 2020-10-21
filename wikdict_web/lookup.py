import sqlite3
import urllib.parse
from datetime import datetime, timedelta
from collections import OrderedDict, deque
from itertools import groupby

from flask import redirect, request, url_for, abort
from markupsafe import Markup

from .languages import language_names
from . import app
from . import base
from .base import timing, db_query


latest_requests = deque(maxlen=30)


def block_too_many_requests(current_ip):
    try:
        lr_list = list(latest_requests)
    except RuntimeError:
        # The latest_requests deque was modified during iteration. Let's just
        # allow this request instead of retrying the check.
        pass
    recent_requests_from_ip = len([
        None for dt, ip in lr_list
        if dt > datetime.now() - timedelta(minutes=1) and ip == current_ip
    ])
    if recent_requests_from_ip > 20:
        abort(429, "You made too many requests. Please contact karl@karl.berlin to resolve this. "
                   "I will provide translation data in an easy to use format. "
                   "If you see this error when normally using the web site, please let me know, too.")
    else:
        latest_requests.append((datetime.now(), current_ip))


def log_query(from_lang, to_lang, query, ip, results):
    try:
        db_query('logging', """
                CREATE TABLE IF NOT EXISTS search_log (
                    ts timestamp DEFAULT current_timestamp, lang1 text, lang2 text,
                    query text, results1, results2, ip, referrer, user_agent, hidden bool DEFAULT false);
            """, path='')
        db_query('logging', """
                    INSERT INTO search_log (lang1, lang2, query,
                                            results1, results2,
                                            ip, referrer, user_agent)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                 [from_lang, to_lang, query, len(results[0]), len(results[1]),
                  ip, request.referrer, request.user_agent.string],
                 path='')
    except sqlite3.OperationalError:
        # It's ok to skip logging the query while the log db is locked
        pass


@app.route('/<from_lang>-<to_lang>/')
@app.route('/<from_lang>-<to_lang>/<path:query>')  # without path, slashes would not be escaped
def lookup(from_lang, to_lang, query=None):
    if from_lang not in language_names or to_lang not in language_names:
        abort(404)
    if [from_lang, to_lang] != sorted((from_lang, to_lang)):
        return redirect(url_for('lookup', from_lang=to_lang, to_lang=from_lang,
                                          query=query))

    templ_vals = {}

    if query:
        results = sorted([
            LangResultList(from_lang, to_lang, query),
            LangResultList(to_lang, from_lang, query),
        ], key=lambda x: x.score, reverse=True)
        if not results[0] and not results[1]:
            templ_vals['did_you_mean'] = spellfix(from_lang, to_lang, query)
        else:
            templ_vals['did_you_mean'] = []

        if request.headers.getlist("X-Forwarded-For"):
            ip = request.headers.getlist("X-Forwarded-For")[0]
        else:
            ip = request.remote_addr
        block_too_many_requests(ip)
        log_query(from_lang, to_lang, query, ip, results)
        wiktionary_links = OrderedDict(
            (key, val)
            for key, val in (
                (lang, get_wiktionary_links(lang, query))
                for lang in (from_lang, to_lang)
            ) if val  # skip langs without results
        )
    else:
        results = None
        wiktionary_links = None
        templ_vals['rough_translations'] = '%.1f' % (
            sum(lp.total_trans for lp in base.get_lang_pairs()) // 100000 / 10
        )
    return base.render_template('lookup.html',
        from_lang=from_lang,
        to_lang=to_lang,
        query=query,
        results=results,
        description=results[0].description if results else None,
        page_name='lookup',
        wiktionary_links=wiktionary_links,
        **templ_vals
    )

@app.route('/lookup')
def lookup_redirect():
    url = '{}/{}'.format(request.args['index_name'], request.args['query'])
    return redirect(url)


class LangResultList:

    def __init__(self, from_lang, to_lang, search_term):
        self.from_lang = from_lang
        self.to_lang = to_lang
        self.results = [
            LexicalEntryResult(list(group), search_term)
            for key, group in groupby(self.search_translations(search_term), key=lambda x: x.lexentry)
        ]
        self.results.sort(key=lambda x: x.score, reverse=True)
        if self.results:
            self.score = self.results[0].score
            self.description = self.make_description()
        else:
            self.score = tuple()
            self.description = None

    def make_description(self):
        lexentry_strs = []
        for lexentry in self.results:
            lexentry_strs.append(lexentry.written_rep + ': ' +
                ', '.join(r.trans_list.replace(' | ', ', ') for r in lexentry)
            )
        description = Markup(' &mdash; ').join(lexentry_strs)
        if len(description) > 160:
            description = description[:159] + Markup('&hellip;')
        return description

    @timing
    def search_translations(self, search_term):
        search_term = '"' + search_term + '"'
        try:
            return db_query(self.from_lang + '-' + self.to_lang, """
                    SELECT *
                    FROM (
                            SELECT DISTINCT written_rep
                            FROM search_trans
                            WHERE form MATCH :term
                        )
                        JOIN translation USING (written_rep)
                    ORDER BY
                        -- only relevant if the limit is active, because we sort on LexicalEntryResult afterwards
                        lower(written_rep) LIKE '%'|| lower(:term) ||'%' DESC, length(written_rep),
                        -- determine the sorting inside each LexicalEntryResult
                        lexentry, coalesce(min_sense_num, '99'), importance * translation_score DESC
                    LIMIT 100
                """, dict(term=search_term))
        except sqlite3.OperationalError as e:
            try:
                error_msg = e.args[0]
            except IndexError:
                raise e
            if "malformed MATCH expression" in error_msg:
                abort(400, 'Invalid search expression')
            else:
                raise e

    def __len__(self):
        return len(self.results)

    def __iter__(self):
        return iter(self.results)


class LexicalEntryResult:

    def __init__(self, results, search_term):
        self.results = results
        self.written_rep = results[0].written_rep
        self.score = (
            self.written_rep == search_term,
            self.written_rep in search_term,
            max(r.translation_score * r.importance for r in results)
        )

    def __len__(self):
        return len(self.results)

    def __iter__(self):
        return iter(self.results)


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


def format_gender(gender):
    if not gender:
        return None
    gender_map = {
        'Neuter': 'n',
        'CommonGender': 'u',
    }
    return gender_map.get(gender, gender[0])


@timing
def vocable_details(vocable, lang, part_of_speech, from_lang, to_lang):
    assert vocable
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
        'gender': format_gender(r.gender),
        'pronuns': set(r.pronun_list.split(' | ')) if r.pronun_list else None,
        'display': r.display or vocable,
        'display_addition': r.display_addition,
        'url': url_for('lookup', from_lang=from_lang, to_lang=to_lang, query=vocable),
    }


@timing
def entry_details(vocable, lexentry, lang, from_lang, to_lang):
    rows = db_query(lang, """
        SELECT *
        FROM entry
        -- Filtering by written_rep allows using the index. Without concerns about performance,
        -- filtering by lexentry only would be sufficient
        WHERE written_rep = ?
          AND lexentry = ?
    """, [vocable, lexentry])
    r = rows[0]._asdict()
    r.update({
        'display': r['display'] or r['written_rep'],
        'display_addition': r['display_addition'],
        'url': url_for('lookup', from_lang=from_lang, to_lang=to_lang, query=vocable),
        'pronuns': r['pronun_list'].split(' | ') if r['pronun_list'] else [],
        'gender': format_gender(r['gender'])
    })
    return r


@timing
def get_wiktionary_links(lang, word):
    url = 'http://%s.wiktionary.org/wiki/%s#%s'
    lang_name = urllib.parse.quote_plus(language_names[lang]).replace('%', '.')
    sql = """
        SELECT written_rep FROM vocable
        WHERE written_lower = lower(?)
    """
    results = []
    for (w, ) in db_query(lang, sql, [word]):
        wiki_name = w.replace(' ', '_')
        results.append((w, url % (lang, wiki_name, lang_name)))
    return results


@app.context_processor
def add_functions():
    return dict(
        vocable_details=vocable_details,
        entry_details=entry_details,
    )
