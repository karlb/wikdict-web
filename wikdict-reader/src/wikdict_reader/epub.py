from pathlib import Path
from typing import Literal, Union
from zipfile import ZipFile

import lxml.builder as builder
from lxml import etree
from lxml.etree import Element, tostring
from lxml.html import fragments_fromstring
from more_itertools import peekable

from .html import format_popup_content, text_to_html_id
from .translate_segments import LookupFunction, translate_segments

nsmap = {
    "xhtml": "http://www.w3.org/1999/xhtml",
    "epub": "http://www.idpf.org/2007/ops",
    "opf": "http://www.idpf.org/2007/opf",
}
E = builder.ElementMaker(nsmap=nsmap)
for ns_short, ns_full in nsmap.items():
    etree.register_namespace(ns_short, ns_full)
BODY_TAG = "{" + nsmap["xhtml"] + "}body"
A_TAG = "{" + nsmap["xhtml"] + "}a"


def trans_markup(trans_id, text, translations):
    el = Element(
        "a",
        {
            "{%s}type" % nsmap["epub"]: "noteref",
            "href": f"#{trans_id}",
            "class": "tr",
        },
    )
    el.text = text
    return el


def format_popup(trans_id: str, trans: dict[str, list]) -> str:
    """Turn query result rows into epub footnote"""
    content = "".join(format_popup_content(trans))
    aside = E.aside(
        *fragments_fromstring(content),
        **{"{%s}type" % nsmap["epub"]: "footnote", "id": trans_id},
    )
    aside.tail = "\n"
    return aside


def get_main_segments(
    elem, attr: Union[Literal["text"], Literal["tail"]], lookup_function: LookupFunction
) -> peekable:
    """Get translation segments for elem.attr

    Handle the special case of the leading segments without translations.
    """
    segments = peekable(translate_segments(getattr(elem, attr), lookup_function))
    setattr(elem, attr, "")

    while True:
        try:
            text, translations = next(segments)
        except StopIteration:
            return segments

        if translations:
            segments.prepend((text, translations))
            return segments
        else:
            setattr(elem, attr, getattr(elem, attr) + text)


def translate_text_in_attr(
    elem,
    attr,
    last_inserted,
    insert,
    used_translations,
    lookup_function: LookupFunction,
) -> None:
    if not getattr(elem, attr):
        return

    for text, translations in get_main_segments(elem, attr, lookup_function):
        if translations:
            trans_id = text_to_html_id(text)
            last_inserted = trans_markup(trans_id, text, translations)
            insert(last_inserted)

            # store id->translations mapping for later insertion
            if trans_id not in used_translations:
                used_translations[trans_id] = translations
        else:
            if last_inserted is None:
                elem.text += text
            else:
                last_inserted.tail = (last_inserted.tail or "") + text


def annotate_element_text(elem, used_translations, lookup_function: LookupFunction):
    """Annote elem.text, the text within elem"""
    i = 0

    def insert(new_element):
        nonlocal i
        elem.insert(i, new_element)
        i += 1

    translate_text_in_attr(elem, "text", None, insert, used_translations, lookup_function)


def annotate_element_tail(elem, used_translations, lookup_function: LookupFunction):
    """Annotate elem.tail, the text right after elem's closing tag"""
    parent = elem.getparent()
    if parent is None:
        return
    i = parent.index(elem)

    def insert(new_element):
        nonlocal i
        parent.insert(i + 1, new_element)
        i += 1

    translate_text_in_attr(elem, "tail", elem, insert, used_translations, lookup_function)


def annotate_file(filename, dir_depth, lookup_function: LookupFunction):
    in_body = False
    in_a = False
    used_translations = {}

    with open(filename, "rb") as f:
        context = etree.iterparse(f, events=("start", "end"))

        # Modifying the elements while parsing is not safe, so we add `list` here
        for event, elem in list(context):
            if elem.tag == BODY_TAG:
                in_body = event == "start"
            elif elem.tag == A_TAG:
                in_a = event == "start"

            if event != "start":
                # Only process each element once, we choose to do it on start
                continue

            if not in_body:
                # We only want to annotate text in the body
                continue

            if in_a:
                # Adding links inside a link is not allowed
                pass
            else:
                annotate_element_text(elem, used_translations, lookup_function)
            annotate_element_tail(elem, used_translations, lookup_function)

    # Add style sheet
    head = context.root.xpath("/xhtml:html/xhtml:head", namespaces=nsmap)[0]
    head.append(
        E.link(
            rel="stylesheet",
            type="text/css",
            href=("../" * dir_depth) + "wikdict_epub.css",
        )
    )

    # Add footnote content to end of body
    body = context.root.xpath("/xhtml:html/xhtml:body", namespaces=nsmap)[0]
    footnote_container = Element("div", style="display:none")
    body.append(footnote_container)
    for trans_id, translations in used_translations.items():
        footnote_container.append(
            format_popup(trans_id, translations),
        )

    etree.cleanup_namespaces(context.root, top_nsmap=nsmap)

    return tostring(context.root, pretty_print=True, encoding="utf-8", xml_declaration=True)


def update_content_opf(filename):
    with open(filename, "rb") as f:
        root = etree.parse(f).getroot()

    manifest = root.xpath("/opf:package/opf:manifest", namespaces=nsmap)[0]
    manifest.append(
        Element(
            "item", id="wikdict-epub-css", href="wikdict_epub.css", **{"media-type": "text/css"}
        )
    )

    return tostring(root, pretty_print=True, encoding=str)


def translate_epub(in_dir: Path | str, out_filename: str, lookup_function: LookupFunction):
    in_dir = Path(in_dir)
    with ZipFile(out_filename, "w") as out_zip:
        # The file "mimetype" must be the first in the zip
        out_zip.writestr("mimetype", "application/epub+zip")
        out_zip.write("html_static/wikdict_epub.css", "wikdict_epub.css")

        for path in in_dir.rglob("*"):
            if not path.is_file():
                continue

            # if path.suffix == ".xhtml" and "chapter02" in path.name:
            if path.suffix in (".xhtml", ".html"):
                print(path)
                file_content = annotate_file(
                    path,
                    dir_depth=len(path.parts) - len(in_dir.parts) - 1,
                    lookup_function=lookup_function,
                )
            elif path.name == "mimetype":
                # Already included above
                continue
            elif path.name == "content.opf":
                file_content = update_content_opf(path)
            else:
                # Keep unchanged
                with open(path, "rb") as f:
                    file_content = f.read()

            out_path = Path(*path.parts[len(in_dir.parts) :])
            out_zip.writestr(str(out_path), file_content)
