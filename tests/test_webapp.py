from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from automated_job_search.webapp import render_page


class WebAppTests(unittest.TestCase):
    def test_render_page_contains_clickable_links(self) -> None:
        page = render_page(
            config_dir=None,
            selected_source_ids=["jobly"],
            raw_keywords="environmental specialist",
        )
        self.assertIn("<!DOCTYPE html>", page)
        self.assertIn(
            'href="https://www.jobly.fi/en/jobs/uusimaa?search=environmental%20specialist&amp;job_geo_location=&amp;Search_jobs=Search+jobs&amp;lat=&amp;lon=&amp;country=&amp;administrative_area_level_1="',
            page,
        )
        self.assertIn("target=\"_blank\"", page)
        self.assertIn("Jobly", page)

    def test_render_page_exposes_junior_toggle_without_listing_terms(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            (config_dir / "keywords.json").write_text(
                json.dumps({"primary": ["environmental"], "junior": ["trainee", "intern"]}),
                encoding="utf-8",
            )
            (config_dir / "sources.json").write_text(
                """
                [
                  {
                    "id": "jobly",
                    "name": "Jobly",
                    "enabled": true,
                    "search_url_template": "https://example.com/{query}"
                  }
                ]
                """,
                encoding="utf-8",
            )
            page = render_page(config_dir=config_dir, selected_source_ids=["jobly"])
            self.assertIn("Include junior keywords as an extra group", page)
            self.assertNotIn("trainee", page)
            junior_page = render_page(config_dir=config_dir, selected_source_ids=["jobly"], include_junior=True)
            self.assertIn("trainee", junior_page)
