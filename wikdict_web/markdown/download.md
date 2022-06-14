## Downloads

WikDict's mission is to bring you dictionaries that can be freely used, copied and modified without limiting you to using this web site. Therefore, you can download the dictionaries in different formats and use them according to the [Creative Commons BY-SA](https://creativecommons.org/licenses/by-sa/3.0/) license.

Please request new formats by creating a [GitHub issue](https://github.com/karlb/wikdict-gen/issues), or just [ask by e-mail](mailto:karl@karl.berlin).

### For End Users

#### StarDict

The [dictionaries in StarDict format](https://download.wikdict.com/dictionaries/stardict/) can be used with a wide variety of different dictionary applications, e.g.:

* [GoldenDict](http://goldendict.org/) for Linux, Windows
* [GoldenDict mobile](http://goldendict.mobi/) for Android (non-free)
* [WordMateX](https://play.google.com/store/apps/details?id=org.d1scw0rld.wordmatex&hl=en) for Android (non-free)
* [Dictionary Universal](https://apps.apple.com/us/app/dictionary-universal/id312088272) for iOS (non-free)
* [KOReader](https://github.com/koreader/koreader) for a variety of e-readers and Android devices

#### Kobo E-Readers

After downloading [dictionaries for Kobo e-readers](https://download.wikdict.com/dictionaries/kobo/), connect your e-reader to your PC and copy the zip file(s) to the `.kobo/dict/` folder on your device. Then disconnect the device and enjoy the new dictionaries!

### For Developers

Apart from the end user oriented dictionaries, the raw information is also available in machine readable formats. Use these to create new applications, language analyses or exports to currently unsupported formats. The data is exported in two different formats:

#### SQLite Databases

This is the native format used by WikDict. [These databases](https://download.wikdict.com/dictionaries/sqlite) contain all information available on the website and all other formats are created by converting from this format. Use the [sqlite3 command line tool](https://sqlite.org/cli.html) or one of the many other database tools with SQLite support to interact with the data.

The data is split up into separate databases, a pair of databases for each language pair (one per direction, mostly containing translation) and one database per language (containing basic information about words, e.g. part of speech, inflections).

To query across multiple databases, use the [`ATTACH DATABASE` command](https://www.sqlite.org/lang_attach.html).

#### TEI P5 (XML)

If you like XML or come from the linguistic community, you may prefer [these XML files](https://download.wikdict.com/dictionaries/tei/recommended/) encoded in [TEI P5](https://www.tei-c.org/Guidelines/P5/). Each language pair has two XML files, one for each translation direction.
