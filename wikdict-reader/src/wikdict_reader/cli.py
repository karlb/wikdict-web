import argparse
import os
import sqlite3
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from urllib.error import HTTPError

import wikdict_compound

from wikdict_reader import make_lookup, translate_epub

DATA_PATH = Path(os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))) / "wikdict"
DATA_PATH = Path(os.environ.get("WIKDICT_DATA_DIR") or DATA_PATH)


def epub():
    import faulthandler

    faulthandler.enable()
    # Parse CLI args
    parser = argparse.ArgumentParser(description="Add translations to the text.")
    parser.add_argument(
        "language_pair",
        help='Pair of languages (ISO 639-1 two-letter codes) combined with a dash, e.g. "en-de"',
    )
    parser.add_argument("input", help="Input file path")
    parser.add_argument("output", nargs="?", help="Output file path (optional)")
    args = parser.parse_args()

    # Detect output path
    if args.output:
        output_path = args.output
    else:
        name, ext = os.path.splitext(args.input)
        output_path = f"{name}_{args.language_pair}{ext}"

    # Configure compound word splitting
    from_lang, to_lang = args.language_pair.split("-")
    if from_lang in wikdict_compound.supported_langs:
        split_lang = from_lang
    else:
        split_lang = None

    # Add translations
    ensure_lang_pair(args.language_pair, compound_db=True)
    conn = sqlite3.connect(DATA_PATH / "wdweb" / f"{args.language_pair}.sqlite3")
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(args.input, "r") as zip_ref:
            zip_ref.extractall(temp_dir)
        translate_epub(
            temp_dir,
            output_path,
            make_lookup(conn, compound_db_path=(DATA_PATH / "compound_dbs"), split_lang=split_lang),
        )

    print(f"Annotated EPUB written to '{output_path}.'")


def ensure_lang_pair(lang_pair, compound_db=False):
    """Downloads necessary dbs to query if not already present

    "de-en" will download "de-en", "de", "en" and if `compound_db` is set it
    will also download "de-compound" (but not "en-compound", since compound
    splitting only needs to be done on the from_lang).
    """
    from_lang, to_lang = lang_pair.split("-")
    ensure_lang(lang_pair)
    ensure_lang(from_lang, compound_db=compound_db)
    ensure_lang(to_lang)
    ensure_db(f"wdweb/{lang_pair}.sqlite3")


def ensure_lang(lang, compound_db=False):
    ensure_db(f"wdweb/{lang}.sqlite3")
    if compound_db:
        try:
            ensure_db(f"compound_dbs/{lang}-compound.sqlite3")
        except HTTPError as e:
            if e.code == 404:
                # Not all languages are supported by the compound splitter
                pass
            else:
                raise


def ensure_db(relative_db_path):
    target = DATA_PATH / relative_db_path
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        url = f"https://download.wikdict.com/dictionaries/{relative_db_path}"
        print("Downloading", url, "to", target, file=sys.stderr)
        urllib.request.urlretrieve(url, target)
