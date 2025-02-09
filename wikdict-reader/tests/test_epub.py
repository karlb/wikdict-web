import re

import pytest
from lxml import etree

import wikdict_reader.epub as epub

from .test_translate_segments import same_lookup


@pytest.mark.parametrize(
    "markup,expected",
    [
        (
            "<p>Content</p>",
            '<p><a epub:type="noteref" href="#tr-Content" class="tr">Content</a></p>',
        ),
        (
            "<div>before<p>Content</p>after</div>",
            '<div>before<p><a epub:type="noteref" href="#tr-Content" class="tr">Content</a></p>after</div>',
        ),
    ],
)
def test_annotate_single_node(markup, expected, monkeypatch):
    root = etree.fromstring(markup)
    epub.annotate_element_text(root.xpath("//*[text()='Content']")[0], {}, same_lookup(["Content"]))
    assert re.sub(r' xmlns:\w+=".*?"', "", etree.tostring(root, encoding="unicode")) == expected


@pytest.mark.parametrize(
    "markup,expected",
    [
        (
            "<p>Content</p>",
            "Content",
        ),
        (
            "<div>before <p>Content</p> after</div>",
            "before Content after",
        ),
        (
            "<p><a>First</a> second <span>third</span></p>",
            "First second third",
        ),
        (
            "<div>before <p><a>First</a> second <span>third</span></p> after</div>",
            "before First second third after",
        ),
        (
            """
                <p class="calibre7">Kung Gustav den tredje var ute på en
                resa<a id="FNanchor_1" class="reference"></a><a class="fnanchor" href="1262393659711613578_51440-h-0.htm_split_003.html#Footnote_1">[1]</a> genom Dalarna. Bråttom hade
                han, och hela vägen ville han åka som i
                sken. Och då det gick med sådan fart,
                att hästarna lågo som sträckta remmar utåt vägen
                och vagnen gick på två hjul i svängarna, stack
                kungen ut huvudet<a id="FNanchor_2" class="reference"></a><a class="fnanchor" href="1262393659711613578_51440-h-0.htm_split_003.html#Footnote_2">[2]</a> genom vagnsfönstret och</p>
            """,
            """Kung Gustav den tredje var ute på en
                resa[1] genom Dalarna. Bråttom hade
                han, och hela vägen ville han åka som i
                sken. Och då det gick med sådan fart,
                att hästarna lågo som sträckta remmar utåt vägen
                och vagnen gick på två hjul i svängarna, stack
                kungen ut huvudet[2] genom vagnsfönstret och""",
        ),
    ],
)
def test_conserve_text(markup, expected, monkeypatch):
    words = re.findall(r"\w+", markup)
    root = etree.fromstring(markup)
    for elem in root.iter():
        epub.annotate_element_text(elem, {}, same_lookup(words))
    print(re.sub(r' xmlns:\w+=".*?"', "", etree.tostring(root, encoding="unicode")))
    assert etree.tostring(root, encoding="unicode", method="text") == expected
