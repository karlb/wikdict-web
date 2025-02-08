import argparse
import os
import sqlite3
import tempfile
import zipfile

import wikdict_compound

from wikdict_reader import make_lookup, translate_epub


def epub():
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
    conn = sqlite3.connect(
        f"/home/karl/code/github/wikdict-web/data/dict/{args.language_pair}.sqlite3"
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(args.input, "r") as zip_ref:
            zip_ref.extractall(temp_dir)
        translate_epub(temp_dir, output_path, make_lookup(conn, split_lang))
