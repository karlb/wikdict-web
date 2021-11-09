import json
from pathlib import Path
from dataclasses import dataclass

"""
languages.json has been queried at https://query.wikidata.org with

SELECT DISTINCT ?lang ?langLabel ?iso3 ?iso2 WHERE {
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
  {
    SELECT DISTINCT ?lang ?iso3 ?iso2
    WHERE {
      ?lang p:P31 ?language_concept;
            wdt:P220 ?iso3;
            wdt:P218 ?iso2.
      ?language_concept (ps:P31/(wdt:P279*)) wd:Q1288568.
    }
  }
}

and afterwards formatted with jq.
"""

LANGUAGE_TO_COUNTRY = {
    # Taken from https://github.com/lipis/flag-icon-css/issues/510#issue-384483599
    "aa": "dj",
    "af": "za",
    "ak": "gh",
    "sq": "al",
    "am": "et",
    "hy": "am",
    "az": "az",
    "bm": "ml",
    "be": "by",
    "bn": "bd",
    "bi": "vu",
    "bs": "ba",
    "bg": "bg",
    "my": "mm",
    "ca": "ad",
    "zh": "cn",
    "hr": "hr",
    "cs": "cz",
    "da": "dk",
    "dv": "mv",
    "nl": "nl",
    "dz": "bt",
    "en": "gb",
    "et": "ee",
    "fj": "fj",
    "fil": "ph",
    "fi": "fi",
    "fr": "fr",
    "gaa": "gh",
    "ka": "ge",
    "de": "de",
    "el": "gr",
    "gu": "in",
    "ht": "ht",
    "he": "il",
    "hi": "in",
    "ho": "pg",
    "hu": "hu",
    "is": "is",
    "ig": "ng",
    "id": "id",
    "ga": "ie",
    "it": "it",
    "ja": "jp",
    "kr": "ne",
    "kk": "kz",
    "km": "kh",
    "kmb": "ao",
    "rw": "rw",
    "kg": "cg",
    "ko": "kr",
    "kj": "ao",
    "ku": "iq",
    "ky": "kg",
    "lo": "la",
    "la": "va",
    "lv": "lv",
    "ln": "cg",
    "lt": "lt",
    "lu": "cd",
    "lb": "lu",
    "mk": "mk",
    "mg": "mg",
    "ms": "my",
    "mt": "mt",
    "mi": "nz",
    "mh": "mh",
    "mn": "mn",
    "mos": "bf",
    "ne": "np",
    "nd": "zw",
    "nso": "za",
    "no": "no",
    "nb": "no",
    "nn": "no",
    "ny": "mw",
    "pap": "aw",
    "ps": "af",
    "fa": "ir",
    "pl": "pl",
    "pt": "pt",
    "pa": "in",
    "qu": "wh",
    "ro": "ro",
    "rm": "ch",
    "rn": "bi",
    "ru": "ru",
    "sg": "cf",
    "sr": "rs",
    "srr": "sn",
    "sn": "zw",
    "si": "lk",
    "sk": "sk",
    "sl": "si",
    "so": "so",
    "snk": "sn",
    "nr": "za",
    "st": "ls",
    "es": "es",
    "ss": "sz",
    "sv": "se",
    "tl": "ph",
    "tg": "tj",
    "ta": "lk",
    "te": "in",
    "tet": "tl",
    "th": "th",
    "ti": "er",
    "tpi": "pg",
    "ts": "za",
    "tn": "bw",
    "tr": "tr",
    "tk": "tm",
    "uk": "ua",
    "umb": "ao",
    "ur": "pk",
    "uz": "uz",
    "ve": "za",
    "vi": "vn",
    "cy": "gb",
    "wo": "sn",
    "xh": "za",
    "zu": "za",
}


@dataclass
class Language:
    label_en: str
    iso3: str
    iso2: str

    @property
    def flag(self):
        """Unicode flag icon for country

        E.g. German flag for de
        """
        country_code = LANGUAGE_TO_COUNTRY[self.iso2]
        return "".join(chr(127365 + ord(c)) for c in country_code)


with open(Path(__file__).parent / "languages.json") as f:
    languages = {
        l["iso2"]: Language(label_en=l["langLabel"], iso2=l["iso2"], iso3=l["iso3"])
        for l in json.load(f)
    }
