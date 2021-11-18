# WikDict Web

This is the web front end for WikDict dictionaries, which is running at [www.wikdict.com].

[www.wikdict.com]: https://www.wikdict.com

# Development Setup

Clone the wikdict-web reposity

    git clone https://github.com/karlb/wikdict-web
    cd wikdict-web

If you have generated dictionaries using [wikdict-gen], link those dictionaries to `data/dict`. If you don't have a local copy of the dictionaries, use the `download_dicts.sh` script to download a complete set of dictionaries.

Now you can run the development server

    ./run_dev.sh

and connect to http://localhost:5000/.

[wikdict-gen]: https://github.com/karlb/wikdict-gen
