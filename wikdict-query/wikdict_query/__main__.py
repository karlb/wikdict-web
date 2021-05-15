import sqlite3
from pprint import pprint
import sys

from wikdict_query import match, format_gender, fetch_idioms, define, combined_result


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
        print(f"{i+1}.", ", ".join(sg["translations"]), end="")
        if sg["senses"]:
            print(" --", ", ".join(sg["senses"]), end="")
        print()


query = sys.argv[1]
conn = sqlite3.connect(
    "/home/karl/code/github/wikdict-gen/dictionaries/wdweb/de-sv.sqlite3"
    # "/home/karl/code/github/wikdict-gen/dictionaries/wdweb/sv-de.sqlite3"
)

# lexentries = list(define(conn, query))

result = combined_result(conn, query)

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
