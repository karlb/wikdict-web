import sqlite3
import sys
from functools import lru_cache
from typing import Callable, Iterable, Optional

import wikdict_compound
import wikdict_query

LookupFunction = Callable[[str], Iterable]


def basic_lookup(cur, phrase: str) -> Iterable:
    try:
        return cur.execute(
            """
            WITH result_block AS (
                SELECT written_rep, form, match_score, importance, sense_groups
                FROM translation_block
                JOIN (
                    SELECT translation_block_rowid, max(form) AS form,
                        max(match_score) AS match_score
                    FROM (
                        SELECT translation_block_rowid, form,
                            score_match(matchinfo(search_by_form, 'cls'), form, :query) AS match_score
                        FROM search_by_form
                        WHERE form MATCH '"^' || :query || '"' 
                        -- workaround: avoid flattening the subquery to make matchinfo work
                        LIMIT -1 OFFSET 0
                    )
                    GROUP BY translation_block_rowid
                ) ON (translation_block_rowid = translation_block.rowid)
            )
            SELECT 
                written_rep,
                form,
                sense_groups,
                max(form) AS form,
                max(match_score) AS match_score,
                max(importance) AS importance
            FROM result_block
            WHERE match_score > (SELECT max(match_score) FROM result_block) / 10
            GROUP BY sense_groups
            ORDER BY max(match_score) * max(importance) DESC
            LIMIT 10
        """,
            dict(query=phrase),
        ).fetchall()
    except sqlite3.OperationalError as e:
        print(f"Lookup failed for {phrase!r}: {e}", file=sys.stderr)
        return []


def compound_lookup(compound_db_path, split_lang, phrase) -> list[str]:
    if not split_lang:
        return []

    split = wikdict_compound.split_compound(
        db_path=compound_db_path,
        lang=split_lang,
        compound=phrase,
        ignore_word=phrase,
    )
    if split is None:
        return []
    if len(split.parts) >= len(phrase) / 3:
        # Too high likelyhood of useless split
        return []
    return split.parts


@lru_cache(maxsize=1024)
def default_lookup(cur, compound_db_path, split_lang, phrase):
    result = basic_lookup(cur, phrase)

    # If we don't find a translation and are down to a single word, try
    # splitting the word into parts and translate them separately.
    if not result and " " not in phrase and len(phrase) >= 4:
        for part in compound_lookup(compound_db_path, split_lang, phrase):
            result += basic_lookup(cur, part.written_rep)

    return result


def make_lookup(
    conn: sqlite3.Connection, compound_db_path, split_lang: Optional[str]
) -> LookupFunction:
    wikdict_query.add_score_match(conn)
    cur = conn.cursor()
    cur.row_factory = sqlite3.Row

    return lambda phrase: default_lookup(cur, compound_db_path, split_lang, phrase)
