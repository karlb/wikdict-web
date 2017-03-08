from flask.json import jsonify

from . import app
from .base import timing, db_query


@app.route('/typeahead/<from_lang>-<to_lang>/<path:query>')
def typeahead(from_lang, to_lang, query):
    rows = db_query(from_lang + '-' + to_lang, """
        SELECT written_rep, replace(trans_list, ' | ', ', ') AS trans_list, lang, max_score, rel_importance
        FROM (
            SELECT written_rep, trans_list, max_score, rel_importance, :from_lang AS lang
            FROM simple_translation
            WHERE written_rep LIKE :query || '%'
            UNION ALL
            SELECT written_rep, trans_list, max_score, rel_importance, :to_lang AS lang
            FROM other.simple_translation
            WHERE written_rep LIKE :query || '%'
        )
        ORDER BY max_score * rel_importance DESC
        """,
        dict(query=query, from_lang=from_lang, to_lang=to_lang),
        attach_dbs=dict(other=to_lang + '-' + from_lang)
    )
    return jsonify(rows)


@app.route('/opensearch/typeahead/<from_lang>-<to_lang>/<path:query>')
def typeahead_opensearch(from_lang, to_lang, query):
    if len(query) < 3:
        return jsonify([])
    rows = db_query(from_lang + '-' + to_lang, """
        SELECT written_rep, replace(trans_list, ' | ', ', ') AS trans_list, lang, max_score, rel_importance
        FROM (
            SELECT written_rep, trans_list, max_score, rel_importance, :from_lang AS lang
            FROM simple_translation
            WHERE written_rep LIKE :query || '%'
            UNION ALL
            SELECT written_rep, trans_list, max_score, rel_importance, :to_lang AS lang
            FROM other.simple_translation
            WHERE written_rep LIKE :query || '%'
        )
        ORDER BY max_score * rel_importance DESC
        """,
                    dict(query=query, from_lang=from_lang, to_lang=to_lang),
                    attach_dbs=dict(other=to_lang + '-' + from_lang)
                    )
    return jsonify([query, [r[0] for r in rows], [r[1] for r in rows]])
