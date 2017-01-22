### What is WikDict?

<img style="float: right; width: 15%" src="/static/img/markdown/by-sa.svg">
WikDict aims to provide free bilingual dictionary data for all use cases. You are currently looking at the WikDict web interface, which provides a simple way to look for translations in the WikDict data. One very important aspect of WikDict is that all data is freely available under a Creative Commons license, which is not the case for most other dictionaries.

---

### The WikDict Web Interface

#### How do I search WikDict?

* Search for single words or common phrases. WikDict can do intelligent lookup in a dictionary, but it can't translate scentences or arbitrary word combinations.
* Don't worry about writing in upper/lower case. Both "haus" and "Haus" will match the dictionary entry "Haus".
* Skip accents and other diacritics if you want to. Typing "Tur" will find "Tür".

---

### The WikDict data

#### Which data is available and where does if come from?

<img style="float: right; width: 15%" src="/static/img/markdown/mit-license.svg">
All data is extracted from [Wiktionary](http://www.wiktionary.org) by the [DBnary](http://kaiko.getalp.org/about-dbnary/) project. So for data to be available, it has to be in one the the Wiktionaries support by DBnary. On top of the extraction work done by DBnary, WikDict

* parses HTML and Wiki formatting from the results to provide proper human-readable output 
* reduces the differences in data structure between different language Wiktionaries
* combines translations from diffrenent language Wiktionaries in a smart way to increase the number of translations
* assigns importance scores to words and translations for better sorting, filtering and suggestions
* merges translations to give more concise output
* converts the data into other formats
* provides a web interface

The source code for all this can be found in the [bitbucket repository](https://bitbucket.org/wikdict/) and is licensed under the MIT license.

#### Data download

The WikDict data is currently provided in two formats:

* A [set of sqlite3 databases](http://download.wikdict.com/dictionaries/sqlite/), which is WikDict's native file format
* XML files according to [TEI P5](http://www.tei-c.org/Guidelines/P5/). This includes only a subset of the available languages and data, currently.

Please don't hesitate to [contact me](mailto:karl42@gmail.com), as I'm interested in this data being used in as many places as possible!

---
<small>MIT logo by [ExcaliburZero](http://excaliburzero.deviantart.com/art/MIT-License-Logo-595847140)</small>