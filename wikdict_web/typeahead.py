from flask.json import jsonify

from . import app
from .base import db_query


def get_typeahead_data(from_lang, to_lang, query, limit=None):
    # SQLite's LIKE folds case for ASCII only, so a lowercase query like "über"
    # would miss capitalised words such as the German noun "Übersetzung". We
    # also match the query with its first letter's case flipped; LIKE then folds
    # the ASCII letters in the rest of the prefix, covering both capitalisations.
    query_alt = query[:1].swapcase() + query[1:]
    sql = """
        SELECT written_rep, replace(trans_list, ' | ', ', ') AS trans_list, lang, max_score, rel_importance
        FROM (
            SELECT written_rep, trans_list, max_score, rel_importance, :from_lang AS lang
            FROM simple_translation
            WHERE written_rep LIKE :query || '%' OR written_rep LIKE :query_alt || '%'
            UNION ALL
            SELECT written_rep, trans_list, max_score, rel_importance, :to_lang AS lang
            FROM other.simple_translation
            WHERE written_rep LIKE :query || '%' OR written_rep LIKE :query_alt || '%'
        )
        ORDER BY max_score * coalesce(rel_importance, 0.01) DESC
    """
    if limit:
        sql += " LIMIT {}".format(limit)
    return db_query(
        from_lang + "-" + to_lang,
        sql,
        dict(query=query, query_alt=query_alt, from_lang=from_lang, to_lang=to_lang),
        attach_dbs=dict(other=to_lang + "-" + from_lang),
    )


def _cached_json(payload):
    # Dictionary data only changes on release, so let clients and any CDN cache
    # typeahead responses instead of hitting the db on every keystroke prefix.
    resp = jsonify(payload)
    resp.headers["Cache-Control"] = "public, max-age=86400"
    return resp


@app.route("/typeahead/<from_lang>-<to_lang>/<path:query>")
def typeahead(from_lang, to_lang, query):
    rows = get_typeahead_data(from_lang, to_lang, query)
    return _cached_json(rows)


@app.route("/opensearch/typeahead/<from_lang>-<to_lang>/<path:query>")
def typeahead_opensearch(from_lang, to_lang, query):
    if len(query) < 2:
        return _cached_json([])
    rows = get_typeahead_data(from_lang, to_lang, query, limit=20)
    return _cached_json([query, [r[0] for r in rows], [r[1] for r in rows]])
