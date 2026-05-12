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
        self.assertIn("Ympäristötieteen alan tehtävät", page)
        self.assertIn('class="menu-toggle"', page)
        self.assertIn('class="keyword-chip"', page)
        self.assertIn('class="chip-toggle"', page)
        self.assertIn('textContent = "+ Show all"', page)
        self.assertIn(
            'href="https://www.jobly.fi/en/jobs/uusimaa?search=environmental%20specialist&amp;job_geo_location=&amp;Search_jobs=Search+jobs&amp;lat=&amp;lon=&amp;country=&amp;administrative_area_level_1="',
            page,
        )
        self.assertIn("target=\"_blank\"", page)
        self.assertIn("Jobly", page)

    def test_render_page_includes_kuntarekry_fixed_link(self) -> None:
        page = render_page(
            config_dir=None,
            selected_source_ids=["kuntarekry"],
            raw_keywords="environmental specialist",
        )
        self.assertIn("Kaikki alan tehtävät", page)
        self.assertIn(
            'href="https://www.kuntarekry.fi/fi/tyopaikat-tehtavan-mukaan/tekninen-ala/ymparistoala/"',
            page,
        )
        self.assertIn("Ympäristöala", page)
        self.assertIn("Kuntarekry - Kaikki alan tehtävät", page)

    def test_render_page_groups_all_jobs_links_into_a_single_section(self) -> None:
        page = render_page(
            config_dir=None,
            selected_source_ids=["jobly-all", "duunitori-all", "kuntarekry"],
            raw_keywords="environmental specialist",
        )
        self.assertIn("Kaikki alan tehtävät", page)
        self.assertIn('class="source-accordion" open', page)
        self.assertEqual(page.count('href="https://www.jobly.fi/en/jobs/enviroment-and-sustainability/uusimaa"'), 1)
        self.assertEqual(
            page.count(
                'href="https://duunitori.fi/tyopaikat?alue=Helsinki%3Bespoo%3Bvantaa&amp;haku=ympäristötieteen+alan+tehtävät+%28ala%29"'
            ),
            1,
        )
        self.assertEqual(
            page.count('href="https://www.kuntarekry.fi/fi/tyopaikat-tehtavan-mukaan/tekninen-ala/ymparistoala/"'),
            1,
        )

    def test_render_page_hides_show_all_for_short_chip_lists(self) -> None:
        page = render_page(
            config_dir=None,
            selected_source_ids=["jobly-all"],
            raw_keywords="environmental specialist",
        )
        self.assertIn('class="chip-shell"', page)
        self.assertIn('id="chip-list-jobly-all"', page)
        self.assertIn('class="chip-toggle" type="button" aria-controls="chip-list-jobly-all" hidden></button>', page)

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
                    "section_label": "Ympäristötieteen alan tehtävät",
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

    def test_render_page_uses_mobile_breakpoint_for_sidebar_and_accordions(self) -> None:
        page = render_page(
            config_dir=None,
            selected_source_ids=["jobly"],
            raw_keywords="environmental specialist",
        )
        self.assertIn('matchMedia("(max-width: 959px)")', page)
        self.assertIn('body.sidebar-open .sidebar', page)
        self.assertIn('accordion.open = false', page)
        self.assertIn('accordion.open = true', page)
