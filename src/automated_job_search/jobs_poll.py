from __future__ import annotations

import asyncio
import html
import os
import random
import re
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urldefrag, urljoin

from .config import SourceDefinition, default_config_dir, load_default_keyword_groups, load_default_sources
from .generation import build_search_url, normalize_keywords


USER_AGENT = "EnvironmentalJobsBot/0.1 (+mailto:your@email)"
DB_PATH = Path("last_seen_urls.sqlite")
RESULT_TABLE_SQL = "CREATE TABLE IF NOT EXISTS seen (url TEXT PRIMARY KEY)"


@dataclass(frozen=True)
class AllowlistEntry:
    kind: str
    family: str
    source_id: str | None = None
    source_name: str | None = None
    url: str | None = None
    label: str | None = None


@dataclass(frozen=True)
class PollTarget:
    source_id: str
    source_name: str
    family: str
    keyword: str
    url: str


POLL_ALLOWLIST: tuple[AllowlistEntry, ...] = (
    AllowlistEntry(kind="keyword_template", family="jobly", source_id="jobly", source_name="Jobly"),
    AllowlistEntry(kind="keyword_template", family="duunitori", source_id="duunitori", source_name="Duunitori"),
    AllowlistEntry(
        kind="fixed_category",
        family="jobly",
        source_name="Jobly",
        url="https://www.jobly.fi/en/jobs/enviroment-and-sustainability/uusimaa",
        label="Enviroment and Sustainability",
    ),
    AllowlistEntry(
        kind="fixed_category",
        family="duunitori",
        source_name="Duunitori",
        url="https://duunitori.fi/tyopaikat/ala/ymparistotieteen-alan-tehtavat",
        label="Ympäristötieteen alan tehtävät",
    ),
)


def _escape_html(value: str) -> str:
    return html.escape(value, quote=False)


def format_alert_message(source_label: str, keyword_label: str, url: str) -> str:
    return (
        f"{_escape_html(source_label)}: New result with keyword <b>{_escape_html(keyword_label)}</b> "
        f"→ {_escape_html(url)}"
    )


def _require_telegram_config() -> tuple[str, str]:
    token = os.getenv("TG_TOKEN", "").strip()
    chat = os.getenv("TG_CHAT", "").strip()
    if not token:
        raise RuntimeError("TG_TOKEN is required to run jobs_poll")
    if not chat:
        raise RuntimeError("TG_CHAT is required to run jobs_poll")
    return token, chat


def _ensure_schema(connection: sqlite3.Connection) -> None:
    connection.execute(RESULT_TABLE_SQL)
    connection.commit()


def _is_seen(connection: sqlite3.Connection, url: str) -> bool:
    row = connection.execute("SELECT 1 FROM seen WHERE url = ?", (url,)).fetchone()
    return row is not None


def _mark_seen(connection: sqlite3.Connection, url: str) -> None:
    connection.execute("INSERT OR IGNORE INTO seen (url) VALUES (?)", (url,))
    connection.commit()


def _load_sources_by_id(config_dir: Path | None = None) -> dict[str, SourceDefinition]:
    config_root = config_dir or default_config_dir()
    sources = load_default_sources(config_root)
    return {source.id: source for source in sources if source.enabled}


def build_poll_targets(config_dir: Path | None = None) -> list[PollTarget]:
    config_root = config_dir or default_config_dir()
    keyword_groups = load_default_keyword_groups(config_root)
    sources_by_id = _load_sources_by_id(config_root)
    targets: list[PollTarget] = []

    for entry in POLL_ALLOWLIST:
        if entry.kind == "keyword_template":
            if not entry.source_id:
                raise RuntimeError("Keyword allowlist entries must define source_id")
            source = sources_by_id.get(entry.source_id)
            if source is None:
                raise RuntimeError(f"Allowlisted source {entry.source_id!r} is missing or disabled")
            keywords = normalize_keywords(keyword_groups.primary + (source.extra_keywords or []))
            for keyword in keywords:
                targets.append(
                    PollTarget(
                        source_id=source.id,
                        source_name=source.name,
                        family=entry.family,
                        keyword=keyword,
                        url=build_search_url(source, keyword),
                    )
                )
            continue

        if entry.kind == "fixed_category":
            if not entry.url or not entry.label:
                raise RuntimeError("Fixed allowlist entries must define url and label")
            targets.append(
                PollTarget(
                    source_id=entry.family,
                    source_name=entry.source_name or entry.family,
                    family=entry.family,
                    keyword=entry.label,
                    url=entry.url,
                )
            )
            continue

        raise RuntimeError(f"Unknown allowlist kind: {entry.kind}")

    return targets


def _extract_candidate_hrefs(html_text: str) -> list[str]:
    return re.findall(r'href=["\']([^"\']+)["\']', html_text, flags=re.IGNORECASE)


def _normalize_url(page_url: str, href: str) -> str:
    absolute_url = urljoin(page_url, href)
    normalized, _fragment = urldefrag(absolute_url)
    return normalized


def extract_jobly_result_urls(html_text: str, page_url: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for href in _extract_candidate_hrefs(html_text):
        if "/job/" not in href and "/tyopaikka/" not in href:
            continue
        absolute_url = _normalize_url(page_url, href)
        if absolute_url in seen:
            continue
        seen.add(absolute_url)
        urls.append(absolute_url)
    return urls


def extract_duunitori_result_urls(html_text: str, page_url: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for href in _extract_candidate_hrefs(html_text):
        if "/tyopaikat/tyo/" not in href:
            continue
        absolute_url = _normalize_url(page_url, href)
        if absolute_url in seen:
            continue
        seen.add(absolute_url)
        urls.append(absolute_url)
    return urls


EXTRACTORS: dict[str, Callable[[str, str], list[str]]] = {
    "jobly": extract_jobly_result_urls,
    "duunitori": extract_duunitori_result_urls,
}


def _fetch_html(url: str) -> str:
    import httpx

    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=15.0) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


async def send_telegram_alert(bot: object, chat_id: str, source_label: str, keyword_label: str, url: str) -> None:
    message = format_alert_message(source_label, keyword_label, url)
    await bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")


def _create_bot(token: str) -> object:
    from telegram import Bot

    return Bot(token=token)


def _load_bot(token: str, bot_factory: Callable[[str], object] | None = None) -> object:
    if bot_factory is not None:
        return bot_factory(token)
    return _create_bot(token)


def _run_send(
    *,
    bot: object,
    chat_id: str,
    source_label: str,
    keyword_label: str,
    url: str,
    send_helper: Callable[[object, str, str, str, str], object] = send_telegram_alert,
) -> None:
    asyncio.run(send_helper(bot, chat_id, source_label, keyword_label, url))


def run_poll(
    *,
    config_dir: Path | None = None,
    db_path: Path = DB_PATH,
    fetch_html: Callable[[str], str] | None = None,
    bot_factory: Callable[[str], object] | None = None,
    send_helper: Callable[[object, str, str, str, str], object] = send_telegram_alert,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> int:
    token, chat_id = _require_telegram_config()
    targets = build_poll_targets(config_dir)
    connection = sqlite3.connect(db_path)
    _ensure_schema(connection)
    bot = _load_bot(token, bot_factory)
    fetch = fetch_html or _fetch_html
    processed_urls: set[str] = set()
    sent_count = 0

    for index, target in enumerate(targets):
        try:
            page_html = fetch(target.url)
        except Exception as exc:  # pragma: no cover - exercised in tests
            print(f"Skipping {target.url}: {exc}", file=sys.stderr)
            if index < len(targets) - 1:
                sleep_fn(random.uniform(2, 5))
            continue

        extractor = EXTRACTORS.get(target.family)
        if extractor is None:
            print(f"Skipping {target.url}: no extractor for family {target.family!r}", file=sys.stderr)
            if index < len(targets) - 1:
                sleep_fn(random.uniform(2, 5))
            continue

        result_urls = extractor(page_html, target.url)
        for result_url in result_urls:
            if result_url in processed_urls or _is_seen(connection, result_url):
                continue
            processed_urls.add(result_url)
            try:
                _run_send(
                    bot=bot,
                    chat_id=chat_id,
                    source_label=target.source_name,
                    keyword_label=target.keyword,
                    url=result_url,
                    send_helper=send_helper,
                )
            except Exception as exc:  # pragma: no cover - exercised in tests
                print(f"Telegram send failed for {result_url}: {exc}", file=sys.stderr)
                continue
            _mark_seen(connection, result_url)
            sent_count += 1

        if index < len(targets) - 1:
            sleep_fn(random.uniform(2, 5))

    return sent_count


def main(config_dir: Path | None = None, db_path: Path = DB_PATH) -> int:
    run_poll(config_dir=config_dir, db_path=db_path)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
