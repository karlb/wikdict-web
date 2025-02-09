from io import StringIO
from typing import Iterable

import wikdict_compound
from flask import request
from markupsafe import Markup, escape
from wikdict_reader import LookupFunction, make_lookup
from wikdict_reader.html import create_partial_html

from . import app, base

MAX_INPUT_BYTES = 4000


def lookup(phrase: str, from_lang: str, simple_lookup: LookupFunction) -> Iterable[str]:
    results = simple_lookup(phrase)
    if results or " " in phrase:
        return results

    # No normal results found, treat the phrase as a compound word and try to split it into parts.
    if from_lang not in wikdict_compound.supported_langs:
        return []
    solution = wikdict_compound.split_compound(
        db_path=base.DATA_DIR / "compound_dbs",
        lang=from_lang,
        compound=phrase,
    )
    if not solution:
        return []
    results = []
    part_reps = [p.written_rep for p in solution.parts]

    # Find translations for each compound word part
    for p in part_reps:
        results += simple_lookup(p)
    return results


@app.route("/reader/<from_lang>-<to_lang>/", methods=["GET", "POST"])
def reader(from_lang, to_lang):
    templ_vals: dict[str, Any] = dict(
        from_lang=from_lang,
        to_lang=to_lang,
    )

    conn = base.get_conn(from_lang + "-" + to_lang)
    annotated_text = None
    if request.method in ["GET", "HEAD"]:
        return base.render_template("reader-input.html", **templ_vals)
    if request.method == "POST":
        # annotate text with translations
        input_text = escape(request.form["text"].strip())
        f = StringIO()
        simple_lookup = make_lookup(conn, from_lang)
        create_partial_html(
            f,
            lambda phrase: lookup(phrase, from_lang, simple_lookup),
            [input_text],
            max_bytes=MAX_INPUT_BYTES,
        )
        annotated_text = Markup(f.getvalue())

        return base.render_template(
            "reader-output.html",
            annotated_text=annotated_text,
            is_truncated=len(input_text) > MAX_INPUT_BYTES,
            **templ_vals,
        )
    raise Exception(f"Bad HTTP method {request.method!r}")
