from __future__ import annotations

import unittest

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
