import argparse
import sqlite3

from wikdict_query import combined_result


def print_result(r):
    print()
    if r["part_of_speech"]:
        pos = f" ({r['part_of_speech']})"
    else:
        pos = ""
    print(
        f"### {r['written_rep']}{pos} {r['match_score']} * {r['translation_score']} * {r['importance']}"
    )
    # if r['gender']:
    #     print('{%s}' % format_gender(r['gender']))

    if r["forms"]:
        print(", ".join(r["forms"]))

    if r["pronuns"]:
        print(", ".join(r["pronuns"]))

    for i, sg in enumerate(r["sense_groups"]):
        print(f"{i + 1}.", ", ".join(sg["translations"]), end="")
        if sg["senses"]:
            print(" --", ", ".join(sg["senses"]), end="")
        print()


parser = argparse.ArgumentParser(prog="python -m wikdict_query")
parser.add_argument("db_filename", metavar="DB_FILENAME", help="Path to SQLite3 file")
parser.add_argument("query", metavar="WORD", help="Word to look up")

config = parser.parse_args()

conn = sqlite3.connect(config.db_filename)

result = combined_result(conn, config.query)

for lexentry in result.definitions:
    # pprint(dict(lexentry))
    print_result(lexentry)

print()

for idiom in result.idioms:
    print(
        idiom["written_rep"],
        "--",
        ", ".join(idiom["translations"]),
        idiom["importance"],
    )
