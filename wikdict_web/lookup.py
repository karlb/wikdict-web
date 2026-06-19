import functools
import sqlite3
import urllib.parse
from collections import OrderedDict, deque
from datetime import datetime, timedelta
from typing import Any

import wikdict_compound
import wikdict_query
from flask import abort, redirect, request, url_for

from . import app, base
from .base import db_query, get_conn, timing
from .languages import language_codes3, language_names

# Map a Wiktionary edition's iso3 code (the `entry.lexentry` prefix, e.g. "fra")
# back to its wiktionary.org subdomain (the iso2 code, e.g. "fr").
edition_to_lang = {iso3: iso2 for iso2, iso3 in language_codes3.items()}

latest_requests: deque[tuple[datetime, str | None]] = deque(maxlen=30)


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
        lr_list = []
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
            write=True,
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
            write=True,
        )
    except sqlite3.OperationalError:
        # It's ok to skip logging the query while the log db is locked
        pass


def get_combined_result(lang, other_lang, query, **kwargs):
    conn = get_conn(lang + "-" + other_lang, cached=True)
    r = wikdict_query.combined_result(conn, query, **kwargs)
    r.from_lang = lang  # type: ignore
    r.to_lang = other_lang  # type: ignore
    return r


@app.route("/<from_lang>-<to_lang>/")
@app.route(
    "/<from_lang>-<to_lang>/<path:query>"
)  # without path, slashes would not be escaped
def lookup(from_lang, to_lang, query: str | None = None):
    if (
        from_lang not in language_names
        or to_lang not in language_names
        or from_lang == to_lang
    ):
        abort(404)
    if [from_lang, to_lang] != sorted((from_lang, to_lang)):
        return redirect(
            url_for("lookup", from_lang=to_lang, to_lang=from_lang, query=query)
        )

    templ_vals: dict[str, Any] = dict(compound_parts=None)
    results = []
    wiktionary_links: OrderedDict[str, list[tuple[str, str]]] | None = None

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
            ip: str | None = request.headers.getlist("X-Forwarded-For")[0]
        else:
            ip = request.remote_addr
        block_too_many_requests(ip)
        log_query(from_lang, to_lang, query, ip, results)
        # Group links by the Wiktionary edition they point to (not the work
        # language), so the label matches the site the link actually opens.
        wiktionary_links = OrderedDict()
        for lang, partner in ((from_lang, to_lang), (to_lang, from_lang)):
            for word, link, edition in get_wiktionary_links(lang, query, partner):
                group = wiktionary_links.setdefault(edition, [])
                if (word, link) not in group:
                    group.append((word, link))
        description = make_description(results[0]) if results else ""
    else:
        wiktionary_links = None
        templ_vals["rough_translations"] = "%.1f" % (
            sum(lp.total_trans for lp in base.get_lang_pairs()) // 100000 / 10
        )
        templ_vals["picker_data"] = base.get_picker_data(from_lang, to_lang)
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
    index_name = request.args["index_name"]
    try:
        from_lang, to_lang = index_name.split("-")
    except ValueError:
        abort(404)
    if from_lang not in language_names or to_lang not in language_names:
        abort(404)
    return redirect(
        url_for("lookup", from_lang=from_lang, to_lang=to_lang, query=request.args["query"])
    )


@app.route("/change-pair")
def change_pair():
    """No-JS fallback for the home-page picker: two selects + submit.

    `lookup()` validates the codes (404) and normalizes their order.
    """
    return redirect("/{}-{}/".format(request.args["from_lang"], request.args["to_lang"]))


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
    if app.config["TESTING"]:
        # Compound dbs are not available in testing setup, yet
        return [], None

    # Collect solutions for both languages
    solutions = []
    for lang, other_lang in [(from_lang, to_lang), (to_lang, from_lang)]:
        if lang not in wikdict_compound.supported_langs:
            continue
        lang_solution = wikdict_compound.split_compound(
            db_path=base.DATA_DIR / "compound_dbs",
            lang=lang,
            compound=query,
            ignore_word=query,
        )
        if not lang_solution:
            continue
        if len(lang_solution.parts) >= len(query) / 3:
            # Too high likelyhood of useless split
            continue
        solutions.append([lang, other_lang, lang_solution])

    if not solutions:
        return [], None

    # Choose result for language with highest score
    solutions.sort(key=lambda x: -x[2].score)
    lang, other_lang, solution = solutions[0]

    # Add details to result
    results = []
    part_reps = [p.written_rep for p in solution.parts]
    for p in part_reps:
        if r := get_combined_result(lang, other_lang, p, include_idioms=False):
            results.append(r)

    return results, part_reps


@timing
def get_wiktionary_links(lang, word, partner=None):
    """Wiktionary links for `word` as (headword, url, edition_lang) tuples.

    WikDict extracts entries from many Wiktionary editions, recorded in the
    `entry.lexentry` prefix (an iso3 code). A word is only guaranteed to have a
    page on an edition it was actually extracted from, so we link to the word's
    own-language edition when it has a native entry and otherwise fall back to a
    source edition that we know contains it (preferring the lookup partner's
    edition, then English). E.g. the Catalan "casa en sèrie" exists only in the
    French and German editions, not ca.wiktionary.org. `edition_lang` is the
    iso2 code of the edition linked to, so callers can label links by it.
    """
    native_anchor = urllib.parse.quote_plus(language_names[lang]).replace("%", ".")
    native_edition = language_codes3.get(lang)
    partner_edition = language_codes3.get(partner)
    sql = """
        SELECT v.written_rep,
               group_concat(DISTINCT substr(e.lexentry, 1, instr(e.lexentry, '/') - 1)) AS sources
        FROM vocable v JOIN entry e ON e.written_rep = v.written_rep
        WHERE v.written_lower = lower(?)
        GROUP BY v.written_rep
    """
    results = []
    for w, sources in db_query(lang, sql, [word]):
        editions = set(sources.split(","))
        wiki_name = urllib.parse.quote(w.replace(" ", "_"))
        if native_edition in editions:
            # The word is in its own-language edition: link there with the
            # language-section anchor, as before.
            link_lang, anchor = lang, native_anchor
        else:
            # Fall back to an edition that actually documents the word,
            # preferring the lookup partner's edition then English. The section
            # anchor is the language name *in that edition's language*, which we
            # don't have, so omit it and let the page load at the top.
            link_lang, anchor = None, None
            for candidate in (partner_edition, "eng", *sorted(editions)):
                if candidate in editions and candidate in edition_to_lang:
                    link_lang = edition_to_lang[candidate]
                    break
            if not link_lang:
                continue  # no edition we can map to a subdomain
        url = "https://%s.wiktionary.org/wiki/%s" % (link_lang, wiki_name)
        if anchor:
            url += "#" + anchor
        results.append((w, url, link_lang))
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
    # Build a plain string (real unicode chars, no HTML entities) so truncation
    # can't slice an entity in half; Jinja escapes it when rendering the tag.
    description = " — ".join(lexentry_strs)
    if len(description) > 160:
        description = description[:159] + "…"
    return description


@app.context_processor
def add_functions():
    return dict(
        format_gender=wikdict_query.format_gender,
        format_pronun=wikdict_query.format_pronun,
    )
