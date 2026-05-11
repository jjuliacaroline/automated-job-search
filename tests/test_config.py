from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from automated_job_search.config import load_default_keyword_groups, load_keywords, load_sources


class ConfigTests(unittest.TestCase):
    def test_load_keywords_preserves_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "keywords.json"
            path.write_text(
                '{"primary": ["one", " two ", "one", ""], "junior": ["junior", " trainee "] }',
                encoding="utf-8",
            )
            self.assertEqual(load_keywords(path), ["one", "two", "one"])
            self.assertEqual(load_keywords(path, include_junior=True), ["one", "two", "one", "junior", "trainee"])

    def test_load_keyword_groups_from_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "keywords.json"
            path.write_text(
                '{"primary": ["main"], "junior": ["intern", "graduate"]}',
                encoding="utf-8",
            )
            groups = load_default_keyword_groups(Path(tmpdir))
            self.assertEqual(groups.primary, ["main"])
            self.assertEqual(groups.junior, ["intern", "graduate"])

    def test_load_sources_from_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sources.json"
            path.write_text(
                """
                [
                  {
                    "id": "example",
                    "name": "Example",
                    "enabled": true,
                    "search_url_template": "https://example.com/search?q={query}",
                    "notes": "Demo"
                  }
                ]
                """,
                encoding="utf-8",
            )
            sources = load_sources(path)
            self.assertEqual(len(sources), 1)
            self.assertEqual(sources[0].id, "example")
            self.assertEqual(sources[0].name, "Example")
            self.assertTrue(sources[0].enabled)
            self.assertIn("{query}", sources[0].url_template)
