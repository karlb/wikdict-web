#!.venv/bin/python
import fileinput
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Iterable, Literal

from wikdict_reader.lookup import make_lookup
from wikdict_reader.translate_segments import translate_segments

STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "html_static"


def text_to_html_id(text: str) -> str:
    # Remove any characters that aren't alphanumeric, hyphen, underscore, colon, or period
    text = re.sub(r"[^\w\-\.:]", "-", text)
    return "tr-" + text


def process_line(f, lookup, line, used_translations) -> None:
    for text, translations in translate_segments(line, lookup):
        if translations:
            trans_id = text_to_html_id(text)
            used_translations[trans_id] = translations
            f.write(f'<a data-translate="{trans_id}" href="#">')

        f.write(text.replace("\n", "<br>\n"))

        if translations:
            f.write("</a>")


def format_popup_content(trans: dict[str, list]) -> Iterable[str]:
    all_shown_translations: set[str] = set()
    for i, t in enumerate(trans):
        # Deduplicate translations across all sense groups of the same translation block
        translations_for_all_senses: dict[str, Literal[True]] = {}  # used dict as ordered set
        for sg in json.loads(t["sense_groups"]):
            translations_for_all_senses |= dict.fromkeys(sg["translations"])

        if set(translations_for_all_senses).issubset(all_shown_translations):
            continue
        else:
            all_shown_translations |= set(translations_for_all_senses)

        # Format translation block
        if i != 0:
            yield "<br>\n"
        yield f"<b>{t['written_rep']}</b>: {', '.join(translations_for_all_senses)}"


def format_popup(trans_id: str, trans: dict[str, list]) -> str:
    """Turn query result rows into HTML output"""
    out = []
    out.append(f'<div id="{trans_id}" class="wd-tooltip">\n')

    out.append('\n<div class="wd-arrow" data-popper-arrow></div>\n')
    out += format_popup_content(trans)
    out.append("</div>\n")
    return "".join(out)


def create_partial_html(f, lookup, lines, max_bytes=float("inf")) -> None:
    f.write(f'<style type="text/css">{open(STATIC_DIR / "reader.css").read()}</style>\n')

    used_translations: dict[str, list] = {}

    # Write annotated text
    f.write('<div class="wd-annotated-text">\n')
    for line in lines:
        line = line[:max_bytes]
        max_bytes -= len(line)

        process_line(f, lookup, line, used_translations)

        if max_bytes == 0:
            break
        print(".", end="", flush=True, file=sys.stderr)
    f.write("</div>\n")

    # Add (initially hidden) annotations
    f.write('<div id="poppers-container">\n')
    for trans_id, trans in used_translations.items():
        f.write(format_popup(trans_id, trans))
    f.write("</div>\n")

    # Add JavaScript code
    f.write(
        f"""
    <script src="https://unpkg.com/@popperjs/core@2"></script>
    <script>{open(STATIC_DIR / 'reader.js').read()}</script>
    """
    )


def create_html_page(f, lookup, lines, max_bytes=float("inf")) -> None:
    f.write('<!DOCTYPE html>\n<meta charset="utf-8" />\n')
    f.write('<meta name="viewport" content="width=device-width, initial-scale=1">\n')
    create_partial_html(f, lookup, lines, max_bytes)


if __name__ == "__main__":
    conn = sqlite3.connect("/home/karl/code/github/wikdict-web/data/dict/sv-de.sqlite3")
    split_lang = "sv"
    create_html_page(sys.stdout, make_lookup(conn, split_lang), fileinput.input(), max_bytes=2000)
