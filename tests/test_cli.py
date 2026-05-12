from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

from automated_job_search.cli import main


class CliTests(unittest.TestCase):
    def _write_keyword_config(self, config_dir: Path, *, primary: list[str], junior: list[str]) -> None:
        (config_dir / "keywords.json").write_text(
            json.dumps({"primary": primary, "junior": junior}),
            encoding="utf-8",
        )

    def test_generate_prints_rows_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            self._write_keyword_config(config_dir, primary=["environmental"], junior=["trainee"])
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
            stdout = io.StringIO()
            exit_code = main(["generate"], config_dir=config_dir, stdout=stdout)
            self.assertEqual(exit_code, 0)
            self.assertIn("https://example.com/environmental", stdout.getvalue())
            self.assertNotIn("trainee", stdout.getvalue())

    def test_generate_csv_writes_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            csv_path = config_dir / "links.csv"
            self._write_keyword_config(config_dir, primary=["environmental"], junior=["trainee"])
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
            stdout = io.StringIO()
            exit_code = main(["generate", "--csv", str(csv_path)], config_dir=config_dir, stdout=stdout)
            self.assertEqual(exit_code, 0)
            self.assertTrue(csv_path.exists())

    def test_generate_keyword_override_uses_explicit_terms(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            self._write_keyword_config(config_dir, primary=["default-term"], junior=["trainee"])
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
            stdout = io.StringIO()
            exit_code = main(["generate", "--keyword", "custom-term"], config_dir=config_dir, stdout=stdout)
            self.assertEqual(exit_code, 0)
            output = stdout.getvalue()
            self.assertIn("custom-term", output)
            self.assertNotIn("default-term", output)

    def test_generate_include_junior_adds_junior_terms(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            self._write_keyword_config(config_dir, primary=["environmental"], junior=["trainee"])
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
            stdout = io.StringIO()
            exit_code = main(["generate", "--include-junior"], config_dir=config_dir, stdout=stdout)
            self.assertEqual(exit_code, 0)
            output = stdout.getvalue()
            self.assertIn("environmental", output)
            self.assertIn("trainee", output)

    def test_generate_fixed_all_jobs_sources_stay_single_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            self._write_keyword_config(config_dir, primary=["environmental", "sustainability"], junior=["trainee"])
            (config_dir / "sources.json").write_text(
                """
                [
                  {
                    "id": "jobly-all",
                    "name": "Jobly - Kaikki alan tehtävät",
                    "enabled": true,
                    "section_label": "Kaikki alan tehtävät",
                    "display_label": "Enviroment and Sustainability",
                    "search_url_template": "https://www.jobly.fi/en/jobs/enviroment-and-sustainability/uusimaa"
                  },
                  {
                    "id": "duunitori-all",
                    "name": "Duunitori - Kaikki alan tehtävät",
                    "enabled": true,
                    "section_label": "Kaikki alan tehtävät",
                    "display_label": "Ympäristötieteen alan tehtävät (ala)",
                    "search_url_template": "https://duunitori.fi/tyopaikat?alue=Helsinki%3Bespoo%3Bvantaa&haku=ympäristötieteen+alan+tehtävät+%28ala%29"
                  }
                ]
                """,
                encoding="utf-8",
            )
            stdout = io.StringIO()
            exit_code = main(
                ["generate", "--source", "jobly-all", "--source", "duunitori-all"],
                config_dir=config_dir,
                stdout=stdout,
            )
            self.assertEqual(exit_code, 0)
            output = stdout.getvalue().splitlines()
            self.assertEqual(len(output), 3)
            self.assertIn("Enviroment and Sustainability", stdout.getvalue())
            self.assertIn("Ympäristötieteen alan tehtävät (ala)", stdout.getvalue())

    def test_open_limit_zero_is_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            self._write_keyword_config(config_dir, primary=["environmental"], junior=["trainee"])
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
            opened = []

            def opener(url: str) -> bool:
                opened.append(url)
                return True

            stdout = io.StringIO()
            exit_code = main(["open", "--limit", "0"], config_dir=config_dir, opener=opener, stdout=stdout)
            self.assertEqual(exit_code, 0)
            self.assertEqual(opened, [])

    def test_serve_does_not_require_browser_opening(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            self._write_keyword_config(config_dir, primary=["environmental"], junior=["trainee"])
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
            from automated_job_search import cli as cli_module

            calls: list[tuple[str, int, bool]] = []

            def fake_serve_app(*, host: str, port: int, config_dir=None, include_junior: bool = False, open_browser: bool = True):
                calls.append((host, port, open_browser))

            original = cli_module.serve_app
            cli_module.serve_app = fake_serve_app
            try:
                stdout = io.StringIO()
                exit_code = main(["serve", "--no-browser"], config_dir=config_dir, stdout=stdout)
            finally:
                cli_module.serve_app = original

            self.assertEqual(exit_code, 0)
            self.assertEqual(calls, [("127.0.0.1", 8000, False)])

    def test_open_invalid_limit_is_rejected_by_parser(self) -> None:
        with self.assertRaises(SystemExit):
            main(["open", "--limit", "not-an-int"], stdout=io.StringIO())
