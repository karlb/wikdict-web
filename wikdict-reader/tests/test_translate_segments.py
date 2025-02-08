import json

import pytest

from wikdict_reader import translate_segments


def same_lookup(known_phrases):
    known_phrases = [p.lower() for p in known_phrases]

    def lookup(phrase):
        if phrase.lower() not in known_phrases:
            return None
        sense_groups = [dict(translations=[phrase])]
        return [dict(sense_groups=json.dumps(sense_groups), form=phrase, match_score=1)]

    return lookup


def dict_lookup(known_phrases: dict):
    known_phrases = {key.lower(): val for key, val in known_phrases.items()}

    def lookup(phrase):
        trans = known_phrases.get(phrase.lower(), None)
        if not trans:
            return None
        sense_groups = [dict(translations=t) for t in trans]
        return [dict(sense_groups=json.dumps(sense_groups), form=phrase, match_score=1)]

    return lookup


@pytest.mark.parametrize(
    "orig_text",
    [
        "Yes, that is true.",
        '"Oh yes", he said.',
        '"Oh yes", he said angrily.',
        "Yes, sure.",
    ],
)
def test_keep_orig_text(orig_text) -> None:
    lookup = same_lookup(["yes", "that", "is", "oh", "yes, sure"])
    segments = list(translate_segments(orig_text, lookup))
    new_text = "".join(segment_text for segment_text, trans in segments)
    assert new_text == orig_text


@pytest.mark.parametrize("orig_text,expected_phrases", [("Yes, sure.", ["Yes, sure"])])
def test_found_phrases(orig_text, expected_phrases):
    lookup = same_lookup(["yes", "that", "is", "oh", "yes, sure"])
    segments = list(translate_segments(orig_text, lookup))
    phrases = [segment_text for segment_text, trans in segments if trans]
    assert phrases == expected_phrases


@pytest.mark.parametrize(
    "orig_text,expected_translations",
    [
        ("Yes, sure.", [["ja"], ["sicher"]]),
        # test deduplication
        # ("Wow", [["wow, hui"]]),
        # ("Gosh", [["wow", "hui"]]),
    ],
)
def test_translations(orig_text, expected_translations):
    lookup = dict_lookup(
        {
            "yes": [["ja"]],
            "sure": [["sicher"]],
            "wow": [["wow", "hui"], ["wow"]],
            "gosh": [["wow"], ["wow", "hui"]],
        }
    )
    segments = list(translate_segments(orig_text, lookup))
    translations = [
        sg["translations"]
        for segment_text, trans in segments
        if trans
        for trans_block in trans
        for sg in json.loads(trans_block["sense_groups"])
    ]
    assert translations == expected_translations
