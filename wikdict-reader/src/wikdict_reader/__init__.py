# Public interface for wikdict_reader
from wikdict_reader.epub import translate_epub
from wikdict_reader.lookup import LookupFunction, make_lookup
from wikdict_reader.translate_segments import translate_segments

__all__ = [translate_segments, LookupFunction, make_lookup, translate_epub]
