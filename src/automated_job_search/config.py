from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SourceDefinition:
    id: str
    name: str
    enabled: bool
    search_url_template: str | None = None
    base_url: str | None = None
    query_encoding: str | None = None
    notes: str | None = None

    @property
    def url_template(self) -> str:
        template = self.search_url_template or self.base_url
        if not template:
            raise ValueError(f"Source {self.id!r} is missing a URL template")
        if "{query}" not in template:
            raise ValueError(f"Source {self.id!r} template must contain '{{query}}' placeholder")
        return template

    @property
    def encoding_style(self) -> str:
        if self.query_encoding is None:
            return "percent"
        if self.query_encoding not in {"percent", "plus"}:
            raise ValueError(f"Source {self.id!r} query_encoding must be 'percent' or 'plus'")
        return self.query_encoding


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_keywords(path: Path) -> list[str]:
    payload = _load_json(path)
    if not isinstance(payload, list):
        raise ValueError("keywords.json must contain a JSON list")
    keywords: list[str] = []
    for item in payload:
        if not isinstance(item, str):
            raise ValueError("keywords.json must contain only strings")
        keyword = item.strip()
        if keyword:
            keywords.append(keyword)
    return keywords


def _coerce_bool(value: Any, field_name: str, source_id: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ValueError(f"Source {source_id!r} field {field_name!r} must be a boolean")


def load_sources(path: Path) -> list[SourceDefinition]:
    payload = _load_json(path)
    if not isinstance(payload, list):
        raise ValueError("sources.json must contain a JSON list")

    sources: list[SourceDefinition] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("sources.json must contain JSON objects")
        source_id = item.get("id")
        name = item.get("name")
        enabled = item.get("enabled")
        search_url_template = item.get("search_url_template")
        base_url = item.get("base_url")
        query_encoding = item.get("query_encoding")
        notes = item.get("notes")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("Each source must include a non-empty string id")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Source {source_id!r} must include a non-empty string name")
        if not isinstance(notes, str) and notes is not None:
            raise ValueError(f"Source {source_id!r} notes must be a string if provided")
        if search_url_template is not None and not isinstance(search_url_template, str):
            raise ValueError(f"Source {source_id!r} search_url_template must be a string if provided")
        if base_url is not None and not isinstance(base_url, str):
            raise ValueError(f"Source {source_id!r} base_url must be a string if provided")
        if query_encoding is not None and not isinstance(query_encoding, str):
            raise ValueError(f"Source {source_id!r} query_encoding must be a string if provided")
        source = SourceDefinition(
            id=source_id.strip(),
            name=name.strip(),
            enabled=_coerce_bool(enabled, "enabled", source_id),
            search_url_template=search_url_template.strip() if isinstance(search_url_template, str) else None,
            base_url=base_url.strip() if isinstance(base_url, str) else None,
            query_encoding=query_encoding.strip() if isinstance(query_encoding, str) else None,
            notes=notes.strip() if isinstance(notes, str) else None,
        )
        sources.append(source)
    return sources


def default_config_dir() -> Path:
    repo_config_dir = Path(__file__).resolve().parents[2] / "config"
    if repo_config_dir.is_dir():
        return repo_config_dir
    return Path(__file__).resolve().parent / "default_config"


def load_default_keywords(config_dir: Path | None = None) -> list[str]:
    return load_keywords((config_dir or default_config_dir()) / "keywords.json")


def load_default_sources(config_dir: Path | None = None) -> list[SourceDefinition]:
    return load_sources((config_dir or default_config_dir()) / "sources.json")
