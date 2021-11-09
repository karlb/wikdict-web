#! /usr/bin/env bash
# Copyright (c) 2021 Sebastian Pipping <sebastian@pipping.org>
# Licensed under the MIT license, see file COPYING for the full text

set -x
set -e

languages=(
    bg
    de
    el
    en
    es
    fi
    fr
    id
    it
    ja
    la
    lt
    mg
    nl
    no
    pl
    pt
    ru
    sv
    tr
)

language_pairs=()
for language_from in "${languages[@]}"; do
    for language_to in "${languages[@]}"; do
        if [[ "${language_from}" = "${language_to}" ]]; then
            continue
        fi

        language_pairs+=( "${language_from}-${language_to}" )
    done
done


for name in wikdict "${languages[@]}" "${language_pairs[@]}"; do
    basename="${name}.sqlite3"
    filename="data/dict/${basename}"

    if [[ -f "${filename}" ]]; then
        continue
    fi

    wget -O "${filename}" "https://download.wikdict.com/dictionaries/wdweb/${basename}"
done
