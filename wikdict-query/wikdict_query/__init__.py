import sqlite3
import json
from pprint import pprint
import sys
from dataclasses import dataclass
from typing import Iterable


def format_gender(gender):
    if not gender:
        return None
    gender_map = {
        "Neuter": "n",
        "CommonGender": "u",
    }
    return gender_map.get(gender, gender[0])


def format_pronun(pronun):
    """Wrap pronunciation in slashes if it is not wrapped"""
    if pronun.startswith("/") or pronun.startswith("["):
        return pronun
    return "/" + pronun + "/"


def literal_query(query):
    """Don't interprete any special query syntax

    SQLite's FTS extensions support special query syntax for AND, OR and
    prefix searches, as well as grouping and negation. There are not of much
    use in the dictionary case, but they break some legitimate queries. So
    let's treat all queries literally by enlosing them in quotes.
    """
    return '"' + query.replace('"', "") + '"'


def fetch_idioms(conn, query):
    """Fetches short translations summary for matches

    Only the base form will be searched, but partial matches will be returned
    for entries with multiple terms.
    """
    cur = conn.cursor()
    cur.row_factory = sqlite3.Row
    for result in cur.execute(
        """
        SELECT DISTINCT written_rep, translations, importance
        FROM idioms
        WHERE written_rep MATCH :written_rep
          AND written_rep != :written_rep
        ORDER BY importance DESC
        LIMIT 10
    """,
        dict(written_rep=literal_query(query)),
    ):
        yield dict(
            written_rep=result["written_rep"],
            translations=json.loads(result["translations"]),
            importance=result["importance"],
        )


def _process_fetched_lexentry(result) -> dict:
    result = dict(result)

    for key in ["sense_groups", "forms", "pronuns"]:
        if result[key]:
            result[key] = json.loads(result[key])

    return result


def _score_match(matchinfo: bytes, form, query) -> float:
    """Score how well the matches form matches the query

    0.5: half of the terms match (using normalized forms)
    1:   all terms match (using normalized forms)
    10:   all terms are identical
    20:   all terms are identical, including case
    """
    # I don't know why the query comes in quoted, but let's remove the quotes
    query = query.strip('"')
    try:
        if form == query:
            return 20
        if form.lower() == query.lower():
            return 10

        # Decode matchinfo blob according to https://www.sqlite.org/fts3.html#matchinfo
        offset = 0
        num_cols = int.from_bytes(matchinfo[offset : offset + 4], sys.byteorder)
        offset += 4
        tokens = int.from_bytes(matchinfo[offset : offset + 4], sys.byteorder)
        offset += num_cols * 4
        matched_tokens = int.from_bytes(matchinfo[offset : offset + 4], sys.byteorder)

        # print(matchinfo, form, query, matched_tokens, tokens)
        return matched_tokens / tokens
    except Exception as e:
        print(e)
        raise


def match(conn, query, limit=10, min_match_score=0) -> Iterable[dict]:
    """Detailed matches for all forms.

    Use min_match_score to restrict results to more exact matches.
    """
    conn.create_function("score_match", 3, _score_match, deterministic=True)
    cur = conn.cursor()
    cur.row_factory = sqlite3.Row
    for result in cur.execute(
        """
            SELECT translation_block.*, match_score,
                match_score * translation_score * importance AS score
            FROM translation_block
                JOIN (
                    SELECT translation_block_rowid,
                        max(match_score) AS match_score
                    FROM (
                        SELECT translation_block_rowid,
                            score_match(matchinfo(search_by_form, 'cls'), form, :query) AS match_score
                        FROM search_by_form
                        WHERE form MATCH :query
                          AND match_score >= :min_match_score
                        -- workaround: avoid flattening the subquery to make matchinfo work
                        LIMIT -1 OFFSET 0
                    )
                    GROUP BY translation_block_rowid
                ) ON translation_block.rowid = translation_block_rowid
            ORDER BY score DESC
            LIMIT :limit
    """,
        dict(query=literal_query(query), limit=limit, min_match_score=min_match_score),
    ):
        yield _process_fetched_lexentry(result)


def define(conn, query) -> Iterable[dict]:
    return match(conn, query, min_match_score=1)
    # cur = conn.cursor()
    # cur.row_factory = sqlite3.Row
    # for result in cur.execute(
    #     "SELECT *, 2 AS match_score FROM translation_block WHERE lower(written_rep) = (?)",
    #     [query],
    # ):
    #     yield _process_fetched_lexentry(result)


@dataclass
class CombinedResult:
    definitions: list
    idioms: list
    score: int

    def __bool__(self) -> bool:
        return bool(self.definitions or self.idioms)

    def __len__(self) -> int:
        return len(self.definitions) + len(self.idioms)


def combined_result(conn, query) -> CombinedResult:
    """Returns both definitions and idioms"""

    definitions = list(define(conn, query))
    idioms = list(fetch_idioms(conn, query))

    # Remove idioms that are already shown in definitions
    idioms = [
        i
        for i in idioms
        if i["written_rep"] not in {d["written_rep"] for d in definitions}
    ]

    return CombinedResult(
        definitions=definitions,
        idioms=idioms,
        score=max(
            max([d["score"] for d in definitions] or [0]),
            max([0.2 * i["importance"] for i in idioms] or [0]),
        ),
    )
