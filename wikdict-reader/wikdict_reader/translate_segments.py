#!.venv/bin/python
import sys
import sqlite3
import re
import json
from dataclasses import dataclass
from typing import Optional, Sequence, Iterable, Iterator, Callable
from more_itertools import seekable  # type: ignore


from wikdict_reader.lookup import LookupFunction

word_re = re.compile(r"(.*?)(\w+)(\W*?$)?", re.DOTALL)


# Monkeypatch rewind support into seekable, see https://github.com/more-itertools/more-itertools/issues/670
def rewind(self, count):
    index = len(self._cache)
    self.seek(max(index - count, 0))


seekable.rewind = rewind


def find_translation_for_longest_phrase_at(
    next_words: seekable, lookup: LookupFunction
):
    """Try to find translations for segments with multiple words.

    Whenever a translation is found, try to find a translation for a phrase
    with one more word. When no new translation is found, return the last found
    translation.

    `phrase` is the part we try to translate. `lead`/`tail` are
    untranslatable strings before/after the phrase. Usually spaces,
    punctuation, etc.
    """
    lead, phrase, tail = next_words.peek().groups()
    search_phrase = phrase
    results = None

    unconfirmed_words: list[str] = []
    first_iteration = True
    while m := next(next_words, None):
        if not first_iteration:
            search_phrase += m.group(1) + m.group(2)
            unconfirmed_words.append(m)

        if '"' in search_phrase:
            break

        search_results = lookup(search_phrase)
        if not search_results:
            break

        # Only results with min_match_score >= 1 (full match) are valid
        # results. But those with lower scores might get better scores when we
        # add more words to the phrase. Therefore, we didn't filter by
        # match_score earlier.
        if good_results := [r for r in search_results if r["match_score"] >= 1]:
            results = good_results
            phrase = search_phrase
            tail = m.group(3)
            unconfirmed_words = []

        first_iteration = False

    # Rewind next_words by number of unconfirmed_words, so that they are processed again
    next_words.rewind(len(unconfirmed_words))

    return phrase, results, lead, tail


# The second element is a list returned by the `lookup` fuction
Segment = tuple[str, Optional[list]]


def find_next_match(next_words, lookup: LookupFunction) -> Iterable[Segment]:
    phrase, results, lead, tail = find_translation_for_longest_phrase_at(
        next_words, lookup
    )

    segments: list[Segment] = [(phrase, list(results) if results else None)]
    if lead:
        segments.insert(0, (lead, None))
    if tail:
        segments.append((tail, None))

    return segments


def translate_segments(input_text: str, lookup: LookupFunction) -> Iterable[Segment]:
    # Yield annotated words
    next_words = seekable(re.finditer(word_re, input_text), maxlen=20)
    while True:
        try:
            yield from find_next_match(next_words, lookup)
        except StopIteration:
            break

    # Yield string after last word
    if next_words.elements():
        end = next_words.elements()[-1].end()
    else:
        # No words found in input_text
        end = 0
    yield input_text[end:], None
