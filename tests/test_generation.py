from __future__ import annotations

import unittest

from automated_job_search.config import SourceDefinition
from automated_job_search.generation import build_search_url, filter_sources, generate_links, normalize_keywords


class GenerationTests(unittest.TestCase):
    def test_url_encoding_handles_spaces_and_finnish_characters(self) -> None:
        source = SourceDefinition(
            id="duunitori",
            name="Duunitori",
            enabled=True,
            search_url_template="https://duunitori.fi/tyopaikat?haku={query}",
        )
        url = build_search_url(source, "ympäristö asiantuntija")
        self.assertEqual(url, "https://duunitori.fi/tyopaikat?haku=ymp%C3%A4rist%C3%B6%20asiantuntija")

    def test_duunitori_template_matches_current_search_shape(self) -> None:
        source = SourceDefinition(
            id="duunitori",
            name="Duunitori",
            enabled=True,
            search_url_template="https://duunitori.fi/tyopaikat?alue=Helsinki%3Bespoo%3Bvantaa&haku={query}",
            query_encoding="plus",
        )
        url = build_search_url(source, "ympäristötieteen alan tehtävät (ala)")
        self.assertEqual(
            url,
            "https://duunitori.fi/tyopaikat?alue=Helsinki%3Bespoo%3Bvantaa&haku=ymp%C3%A4rist%C3%B6tieteen+alan+teht%C3%A4v%C3%A4t+%28ala%29",
        )

    def test_jobly_template_matches_current_search_shape(self) -> None:
        source = SourceDefinition(
            id="jobly",
            name="Jobly",
            enabled=True,
            search_url_template=(
                "https://www.jobly.fi/en/jobs/uusimaa?search={query}"
                "&job_geo_location=&Search_jobs=Search+jobs&lat=&lon=&country=&administrative_area_level_1="
            ),
        )
        url = build_search_url(source, "sustainability")
        self.assertEqual(
            url,
            "https://www.jobly.fi/en/jobs/uusimaa?search=sustainability&job_geo_location=&Search_jobs=Search+jobs&lat=&lon=&country=&administrative_area_level_1=",
        )

    def test_kuntarekry_uses_fixed_search_url_without_terms(self) -> None:
        source = SourceDefinition(
            id="kuntarekry",
            name="Kuntarekry",
            enabled=True,
            search_url_template=(
                "https://www.kuntarekry.fi/fi/tyopaikat/?&location=39022%2C39496%2C39498%2C39500%2C39502%2C39504%2C39506%2C39508%2C39510%2C39512%2C39514%2C39024%2C39516%2C39026%2C39028%2C39518%2C39520%2C39522%2C39030%2C39032%2C39524%2C39034%2C39526%2C39528%2C39530%2C39532&profession=38858"
            ),
        )
        url = build_search_url(source, "environmental")
        self.assertEqual(
            url,
            "https://www.kuntarekry.fi/fi/tyopaikat/?&location=39022%2C39496%2C39498%2C39500%2C39502%2C39504%2C39506%2C39508%2C39510%2C39512%2C39514%2C39024%2C39516%2C39026%2C39028%2C39518%2C39520%2C39522%2C39030%2C39032%2C39524%2C39034%2C39526%2C39528%2C39530%2C39532&profession=38858",
        )

    def test_source_filtering_uses_enabled_sources_and_ids(self) -> None:
        sources = [
            SourceDefinition(id="jobly", name="Jobly", enabled=True, search_url_template="https://example.com/{query}"),
            SourceDefinition(id="duunitori", name="Duunitori", enabled=False, search_url_template="https://example.com/{query}"),
            SourceDefinition(id="kuntarekry", name="Kuntarekry", enabled=True, search_url_template="https://example.com/{query}"),
        ]
        filtered = filter_sources(sources, ["kuntarekry", "jobly"])
        self.assertEqual([source.id for source in filtered], ["jobly", "kuntarekry"])

    def test_keyword_normalization_and_generation(self) -> None:
        source = SourceDefinition(id="jobly", name="Jobly", enabled=True, search_url_template="https://example.com/{query}")
        keywords = normalize_keywords([" environmental ", "environmental", "trainee"])
        self.assertEqual(keywords, ["environmental", "trainee"])
        rows = generate_links([source], keywords)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].keyword, "environmental")
        self.assertEqual(rows[1].url, "https://example.com/trainee")
