import threading
import unittest

from flask_testing import TestCase

import wikdict_web
from wikdict_web import base, lookup


class MyTestCase(TestCase):
    def create_app(self):
        wikdict_web.app.config["TESTING"] = True
        return wikdict_web.app

    def test_root(self):
        rv = self.client.get("/")
        self.assertEqual(rv.status_code, 200)

    def test_home(self):
        rv = self.client.get("/de-en/")
        assert rv.status_code == 200

    def test_find(self):
        rv = self.client.get("/de-en/Haus")
        assert rv.status_code == 200
        assert "house".encode("utf-8") in rv.data

    def test_miss(self):
        # A nonsense word that has no entry and doesn't split into a compound,
        # so it stays a genuine miss even with compound lookup enabled.
        rv = self.client.get("/de-en/Xqzwktph")
        assert rv.status_code == 200
        assert "Sorry".encode("utf-8") in rv.data

    def test_did_you_mean(self):
        # A misspelling with no direct hit surfaces spellfix suggestions.
        rv = self.client.get("/de-en/Hauss")
        assert rv.status_code == 200
        assert b"Did you mean" in rv.data
        assert "Haus".encode("utf-8") in rv.data

    def test_concurrent_lookups(self):
        # Regression test: cached db connections must be per-thread. A shared
        # connection broke under concurrency with "Error creating function"
        # (score_match registered while another thread used the connection).
        words = ["Haus", "Wasser", "Sprache", "Tisch", "Buch", "Katze"]
        bad = []

        def worker(n):
            for i in range(12):
                # distinct IP per request so the rate limiter doesn't interfere
                headers = {"X-Forwarded-For": f"198.51.{n}.{i}"}
                rv = self.client.get("/de-en/" + words[(n + i) % len(words)],
                                     headers=headers)
                if rv.status_code != 200:
                    bad.append(rv.status_code)

        threads = [threading.Thread(target=worker, args=(n,)) for n in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not bad, f"non-200 responses under concurrency: {bad}"

    def test_invalid_pair_is_404(self):
        assert self.client.get("/xx-yy/").status_code == 404

    def test_swapped_pair_redirects(self):
        rv = self.client.get("/en-de/Haus")
        assert rv.status_code in (301, 302)
        assert "/de-en/Haus" in rv.headers["Location"]

    def test_typeahead(self):
        rv = self.client.get("/typeahead/de-en/hau")
        assert rv.status_code == 200
        assert isinstance(rv.get_json(), list)
        assert "max-age" in rv.headers.get("Cache-Control", "")

    def test_typeahead_opensearch(self):
        rv = self.client.get("/opensearch/typeahead/de-en/haus")
        assert rv.status_code == 200
        payload = rv.get_json()
        assert payload[0] == "haus"
        assert isinstance(payload[1], list)

    def test_lookup_redirect(self):
        rv = self.client.get("/lookup?index_name=de-en&query=Haus")
        assert rv.status_code in (301, 302)
        assert "/de-en/Haus" in rv.headers["Location"]

    def test_lookup_redirect_rejects_open_redirect(self):
        rv = self.client.get("/lookup?index_name=https://evil.com&query=x")
        assert rv.status_code == 404

    def test_opensearch_xml(self):
        rv = self.client.get("/opensearch/de-en")
        assert rv.status_code == 200
        assert b"OpenSearchDescription" in rv.data

    def test_page(self):
        assert self.client.get("/page/about").status_code == 200
        assert self.client.get("/page/does-not-exist").status_code == 404

    def test_reader_get(self):
        assert self.client.get("/reader/de-en/").status_code == 200

    def test_reader_post(self):
        rv = self.client.post("/reader/de-en/", data={"text": "Haus"})
        assert rv.status_code == 200

    def test_reader_invalid_pair_is_404(self):
        assert self.client.get("/reader/xx-yy/").status_code == 404

    def test_admin_requires_auth(self):
        assert self.client.get("/admin/").status_code == 401

    @unittest.skipUnless(
        (base.COMPOUND_DB_PATH / "de-compound.sqlite3").exists(),
        "compound db not available",
    )
    def test_compound_split(self):
        rv = self.client.get("/de-en/Haustür")
        assert rv.status_code == 200
        # The compound is shown split into its parts.
        assert "Tür".encode("utf-8") in rv.data


def _result(definitions):
    r = type("R", (), {})()
    r.definitions = definitions
    return r


class UnitTests(unittest.TestCase):
    def test_make_description_preserves_special_chars(self):
        desc = _result(
            [{"written_rep": "A&B", "sense_groups": [{"translations": ["x", "y"]}]}]
        )
        assert lookup.make_description(desc) == "A&B: x, y"

    def test_make_description_truncates_without_breaking(self):
        desc = _result(
            [{"written_rep": "w" * 200, "sense_groups": [{"translations": ["t" * 200]}]}]
        )
        result = lookup.make_description(desc)
        assert len(result) <= 160
        assert result.endswith("…")

    def test_anonymize_ip(self):
        assert lookup.anonymize_ip("203.0.113.42") == "203.0.113.0"
        assert lookup.anonymize_ip("2001:db8:abcd:1234::1") == "2001:db8:abcd::"
        assert lookup.anonymize_ip(None) is None
        assert lookup.anonymize_ip("") == ""

    def test_get_wiktionary_links_native_edition(self):
        with wikdict_web.app.test_request_context("/"):
            links = lookup.get_wiktionary_links("de", "Haus", "en")
        words = {word for word, _url, _edition in links}
        assert "Haus" in words
        haus_url = next(url for word, url, _ in links if word == "Haus")
        assert haus_url.startswith("https://de.wiktionary.org/")

    def test_get_picker_data_structure(self):
        with wikdict_web.app.test_request_context("/"):
            data = base.get_picker_data("de", "en")
        assert data["current"] == ["de", "en"]
        assert data["languages"]
        assert set(data["languages"][0]) == {"code", "name", "flag", "partners"}


if __name__ == "__main__":
    unittest.main()
