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

