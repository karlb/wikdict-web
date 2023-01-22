import sqlite3
import urllib.parse
from datetime import datetime, timedelta
from collections import OrderedDict, deque
from itertools import groupby
from typing import Tuple, Any
import functools

from flask import redirect, request, url_for, abort
from markupsafe import Markup
import wikdict_query
import wikdict_compound

from .languages import language_names
from . import app
from . import base
from .base import timing, db_query, get_conn


latest_requests = deque(maxlen=30)


def lru_cache(*args, **kwargs):
    if app.debug:
        return args[0]
    else:
        return functools.lru_cache(*args, **kwargs)


def block_too_many_requests(current_ip):
    try:
        lr_list = list(latest_requests)
    except RuntimeError:
        # The latest_requests deque was modified during iteration. Let's just
        # allow this request instead of retrying the check.
        pass
    recent_requests_from_ip = len(
        [
            None
            for dt, ip in lr_list
            if dt > datetime.now() - timedelta(minutes=1) and ip == current_ip
        ]
    )
    if recent_requests_from_ip > 20:
        abort(
            429,
            "You made too many requests. Please contact karl@karl.berlin to resolve this. "
            "I will provide translation data in an easy to use format. "
            "If you see this error when normally using the web site, please let me know, too.",
        )
    else:
        latest_requests.append((datetime.now(), current_ip))


def log_query(from_lang, to_lang, query, ip, results):
    try:
        db_query(
            "logging",
            """
                CREATE TABLE IF NOT EXISTS search_log (
                    ts timestamp DEFAULT current_timestamp, lang1 text, lang2 text,
                    query text, results1, results2, ip, referrer, user_agent, hidden bool DEFAULT false);
            """,
            path="",
        )
        db_query(
            "logging",
            """
                    INSERT INTO search_log (lang1, lang2, query,
                                            results1, results2,
                                            ip, referrer, user_agent)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
            [
                from_lang,
                to_lang,
                query,
                sum(len(r) for r in results if r.from_lang == from_lang),
                sum(len(r) for r in results if r.from_lang == to_lang),
                ip,
                request.referrer,
                request.user_agent.string,
            ],
            path="",
        )
    except sqlite3.OperationalError:
        # It's ok to skip logging the query while the log db is locked
        pass


def get_combined_result(lang, other_lang, query, **kwargs):
    conn = get_conn(lang + "-" + other_lang)
    r = wikdict_query.combined_result(conn, query, **kwargs)
    r.from_lang = lang  # type: ignore
    r.to_lang = other_lang  # type: ignore
    return r


@app.route("/<from_lang>-<to_lang>/")
@app.route(
    "/<from_lang>-<to_lang>/<path:query>"
)  # without path, slashes would not be escaped
def lookup(from_lang, to_lang, query: str = None):
    if from_lang not in language_names or to_lang not in language_names:
        abort(404)
    if [from_lang, to_lang] != sorted((from_lang, to_lang)):
        return redirect(
            url_for("lookup", from_lang=to_lang, to_lang=from_lang, query=query)
        )

    templ_vals: dict[str, Any] = dict(compound_parts=None)
    results = []

    if query:
        for lang, other_lang in [(from_lang, to_lang), (to_lang, from_lang)]:
            if r := get_combined_result(lang, other_lang, query):
                results.append(r)
        results.sort(key=lambda r: -r.score)

        if not results:
            compound_results, templ_vals["compound_parts"] = get_compounds(
                from_lang, to_lang, query
            )
            results += compound_results
        if not results:
            templ_vals["did_you_mean"] = spellfix(from_lang, to_lang, query)
        else:
            templ_vals["did_you_mean"] = []

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
            )
            if val  # skip langs without results
        )
        description = make_description(results[0]) if results else ""
    else:
        wiktionary_links = None
        templ_vals["rough_translations"] = "%.1f" % (
            sum(lp.total_trans for lp in base.get_lang_pairs()) // 100000 / 10
        )
        description = "Free bilingual dictionaries for many languages"
    return base.render_template(
        "lookup.html",
        from_lang=from_lang,
        to_lang=to_lang,
        query=query,
        results=results,
        description=description,
        page_name="lookup",
        wiktionary_links=wiktionary_links,
        **templ_vals,
    )


@app.route("/lookup")
def lookup_redirect():
    url = "{}/{}".format(request.args["index_name"], request.args["query"])
    return redirect(url)


@lru_cache
@timing
def spellfix(from_lang, to_lang, search_term):
    translated_fixes = db_query(
        from_lang + "-" + to_lang,
        """
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
            lang=from_lang, other_lang=to_lang, other_pair=to_lang + "-" + from_lang
        ),
    )
    return [r.word for r in translated_fixes]


@lru_cache
@timing
def get_compounds(from_lang, to_lang, query):
    results = []
    part_reps = None
    for lang, other_lang in [(from_lang, to_lang), (to_lang, from_lang)]:
        if lang not in wikdict_compound.supported_langs:
            continue
        solution = wikdict_compound.split_compound(
            db_path=base.DATA_DIR / "compound_dbs",
            lang=lang,
            compound=query,
        )
        if not solution:
            continue
        part_reps = [p.written_rep for p in solution.parts]
        for p in part_reps:
            if r := get_combined_result(lang, other_lang, p, include_idioms=False):
                results.append(r)
        break
    return results, part_reps


@timing
def get_wiktionary_links(lang, word):
    url = "https://%s.wiktionary.org/wiki/%s#%s"
    lang_name = urllib.parse.quote_plus(language_names[lang]).replace("%", ".")
    sql = """
        SELECT written_rep FROM vocable
        WHERE written_lower = lower(?)
    """
    results = []
    for (w,) in db_query(lang, sql, [word]):
        wiki_name = w.replace(" ", "_")
        results.append((w, url % (lang, wiki_name, lang_name)))
    return results


def make_description(results: wikdict_query.CombinedResult):
    """Generate description for HTML meta tag, useful for search engines"""
    lexentry_strs = []
    for lexentry in results.definitions:
        lexentry_strs.append(
            lexentry["written_rep"]
            + ": "
            + ", ".join(
                ", ".join(sg["translations"]) for sg in lexentry["sense_groups"]
            )
        )
    description = Markup(" &mdash; ").join(lexentry_strs)
    if len(description) > 160:
        description = description[:159] + Markup("&hellip;")
    return description


@app.context_processor
def add_functions():
    return dict(
        format_gender=wikdict_query.format_gender,
        format_pronun=wikdict_query.format_pronun,
    )
