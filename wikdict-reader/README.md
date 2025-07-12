# What is WikDict Reader?

It can take existing texts and link dictionary entries to the items found in the text. WikDict Reader can
* use conjugated forms for lookup
* [split compound words](https://github.com/karlb/wikdict-compound) and look up the words separately if the complete compound is not in the dictionary
* look up multi word phrases (if those are in the dictionary)
* create results that can be used without requiring the user to install a dictionary

## Installation

I recommend using [uv](https://docs.astral.sh/uv/) to install it:
```
uv tool install "wikdict-reader @ git+https://github.com/karlb/wikdict-web#subdirectory=wikdict-reader"
```

## Web

The WikDict website runs [a web version of WikDict Reader](https://www.wikdict.com/reader/de-en/)

## EPUB

You can use WikDict Reader to add translations to books in EPUB3 format.

After installation, the `translate_epub` command should be available. You can annotate your English EPUB with German translations by calling
```
translate_epub en-de my_book.epub
```
This works for all language pairs supported by WikDict. See `translate_epub --help` for more options.

### Supported Readers

- [KOReader](https://koreader.rocks/)
- Kobo e-readers (if the EPUB is transformed to a kepub, e.g. with [kepubify](https://pgaskin.net/kepubify/try/))
- [Foliate](https://johnfactotum.github.io/foliate/)

Some readers have problems with the pop-up footnotes or the sheer amount of links/footnotes inserted. If you try this out, please [let me know how it went](mailto:karl@karl.berlin)!
