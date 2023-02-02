import sys
from functools import lru_cache
import sqlite3
from typing import Iterable, Callable

import wikdict_query  # type: ignore


LookupFunction = Callable[[str], Iterable]


@lru_cache(maxsize=1024)
def default_lookup(cur, phrase: str) -> Iterable:
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


def make_lookup(conn: sqlite3.Connection) -> LookupFunction:
    wikdict_query.add_score_match(conn)
    cur = conn.cursor()
    cur.row_factory = sqlite3.Row

    return lambda phrase: default_lookup(cur, phrase)
