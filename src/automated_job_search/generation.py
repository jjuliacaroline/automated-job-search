from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote, quote_plus

from .config import SourceDefinition


@dataclass(frozen=True)
class GeneratedLink:
    source_id: str
    source_name: str
    keyword: str
    url: str


def normalize_keywords(keywords: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for keyword in keywords:
        cleaned = keyword.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        ordered.append(cleaned)
    return ordered


def filter_sources(sources: list[SourceDefinition], selected_source_ids: list[str] | None) -> list[SourceDefinition]:
    enabled_sources = [source for source in sources if source.enabled]
    if not selected_source_ids:
        return enabled_sources

    wanted = {source_id.strip().lower() for source_id in selected_source_ids if source_id.strip()}
    filtered = [
        source
        for source in enabled_sources
        if source.id.lower() in wanted or source.name.lower() in wanted
    ]
    if not filtered:
        raise ValueError("No enabled sources matched the requested filter")
    return filtered


def build_search_url(source: SourceDefinition, keyword: str) -> str:
    if source.encoding_style == "plus":
        encoded_keyword = quote_plus(keyword.strip(), safe="")
    else:
        encoded_keyword = quote(keyword.strip(), safe="")
    return source.url_template.format(query=encoded_keyword)


def generate_links(
    sources: list[SourceDefinition],
    keywords: list[str],
) -> list[GeneratedLink]:
    rows: list[GeneratedLink] = []
    for source in sources:
        for keyword in keywords:
            rows.append(
                GeneratedLink(
                    source_id=source.id,
                    source_name=source.name,
                    keyword=keyword,
                    url=build_search_url(source, keyword),
                )
            )
    return rows
