from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from automated_job_search.config import load_keywords, load_sources


class ConfigTests(unittest.TestCase):
    def test_load_keywords_preserves_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "keywords.json"
            path.write_text('["one", " two ", "one", ""]', encoding="utf-8")
            self.assertEqual(load_keywords(path), ["one", "two", "one"])

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

