#!/usr/bin/env python3
import json

language_names = {}
language_codes3 = {}

with open("languages/languages.tsv", encoding="utf-8") as f:
    for line in f:
        fields = line.split("\t")
        language_names[fields[3]] = fields[2].split(",")[0]
        language_codes3[fields[3]] = fields[4]


def emit(name, d):
    lines = [name + " = {"]
    for k, v in d.items():
        key = json.dumps(k, ensure_ascii=False)
        value = json.dumps(v, ensure_ascii=False)
        lines.append(f"    {key}: {value},")
    lines.append("}")
    return "\n".join(lines)


with open("languages/__init__.py", "w", encoding="utf-8") as f:
    f.write(emit("language_names", language_names) + "\n\n")
    f.write(emit("language_codes3", language_codes3) + "\n")
