from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

from automated_job_search.cli import main


class CliTests(unittest.TestCase):
    def test_generate_prints_rows_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            (config_dir / "keywords.json").write_text('["environmental"]', encoding="utf-8")
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

    def test_generate_csv_writes_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            csv_path = config_dir / "links.csv"
            (config_dir / "keywords.json").write_text('["environmental"]', encoding="utf-8")
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
            (config_dir / "keywords.json").write_text('["default-term"]', encoding="utf-8")
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

    def test_open_limit_zero_is_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            (config_dir / "keywords.json").write_text('["environmental"]', encoding="utf-8")
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

    def test_open_invalid_limit_is_rejected_by_parser(self) -> None:
        with self.assertRaises(SystemExit):
            main(["open", "--limit", "not-an-int"], stdout=io.StringIO())
