from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from automated_job_search.csv_export import CSV_HEADERS, write_csv
from automated_job_search.generation import GeneratedLink


class CsvTests(unittest.TestCase):
    def test_csv_export_shape_and_headers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "links.csv"
            rows = [
                GeneratedLink(
                    source_id="jobly",
                    source_name="Jobly",
                    keyword="environmental",
                    url="https://example.com/environmental",
                )
            ]
            write_csv(rows, path)

            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, CSV_HEADERS)
                data = list(reader)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["source_id"], "jobly")
            self.assertEqual(data[0]["keyword"], "environmental")

