from __future__ import annotations

import csv
from pathlib import Path

from .generation import GeneratedLink


CSV_HEADERS = ["source_id", "source_name", "keyword", "url"]


def write_csv(rows: list[GeneratedLink], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "source_id": row.source_id,
                    "source_name": row.source_name,
                    "keyword": row.keyword,
                    "url": row.url,
                }
            )

