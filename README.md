# WikDict Web

This is the web front end for WikDict dictionaries, which is running at [www.wikdict.com].

[www.wikdict.com]: http://www.wikdict.com

# Development Setup

Clone the wikdict-web reposity

    hg clone ssh://hg@bitbucket.org/wikdict/wikdict-web
    cd wikdict-web

and setup a virtualenv to your process to run in

    virtualenv -p python3 venv

If you have generated dictionaries using [wikdict-gen], link those dictionaries to `data/dict`. If you don't have a local copy of the dictionaries, use the `download_dicts.sh` script to download a complete set of dictionaries.

Now you can run the development server

    ./run_dev.sh

and connect to http://localhost:4000/.