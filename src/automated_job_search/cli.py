from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TextIO

from .browser import open_urls
from .config import KeywordGroups, default_config_dir, load_default_keyword_groups, load_default_sources
from .csv_export import write_csv
from .generation import filter_sources, generate_links, normalize_keywords
from .webapp import serve_app


def _add_common_generation_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        default=None,
        help="Limit output to one or more source ids.",
    )
    parser.add_argument(
        "--keyword",
        action="append",
        dest="keywords",
        default=None,
        help="Use one or more explicit keywords instead of the configured defaults.",
    )
    parser.add_argument(
        "--csv",
        dest="csv_path",
        type=Path,
        default=None,
        help="Write generated rows to a CSV file.",
    )
    parser.add_argument(
        "--include-junior",
        action="store_true",
        help="Include the optional junior keyword group.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="automated-job-search")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser("generate", help="Generate search links.")
    _add_common_generation_arguments(generate_parser)

    open_parser = subparsers.add_parser("open", help="Open a limited number of generated links.")
    open_parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="Maximum number of links to open. Defaults to a conservative cap of 3.",
    )
    open_parser.add_argument(
        "--include-junior",
        action="store_true",
        help="Include the optional junior keyword group.",
    )

    serve_parser = subparsers.add_parser("serve", help="Run a local web UI for generated links.")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind to.")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port to bind to.")
    serve_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not auto-open the web UI in a browser.",
    )
    serve_parser.add_argument(
        "--include-junior",
        action="store_true",
        help="Include the optional junior keyword group.",
    )
    return parser


def _load_generation_inputs(config_dir: Path | None = None) -> tuple[KeywordGroups, list]:
    config_root = config_dir or default_config_dir()
    keywords = load_default_keyword_groups(config_root)
    sources = load_default_sources(config_root)
    return keywords, sources


def _select_keywords(
    explicit_keywords: list[str] | None,
    keyword_groups,
    include_junior: bool,
) -> list[str]:
    if explicit_keywords:
        selected = list(explicit_keywords)
    else:
        selected = list(keyword_groups.primary)
    if include_junior:
        selected.extend(keyword_groups.junior)
    return normalize_keywords(selected)


def _print_rows(rows, stdout: TextIO) -> None:
    stdout.write("source_id\tsource_name\tkeyword\turl\n")
    for row in rows:
        stdout.write(f"{row.source_id}\t{row.source_name}\t{row.keyword}\t{row.url}\n")


def run_generate(
    *,
    sources_filter: list[str] | None = None,
    explicit_keywords: list[str] | None = None,
    csv_path: Path | None = None,
    include_junior: bool = False,
    config_dir: Path | None = None,
    stdout: TextIO = sys.stdout,
) -> list:
    keyword_groups, sources = _load_generation_inputs(config_dir)
    selected_sources = filter_sources(sources, sources_filter)
    selected_keywords = _select_keywords(explicit_keywords, keyword_groups, include_junior)
    rows = generate_links(selected_sources, selected_keywords)
    _print_rows(rows, stdout)
    if csv_path is not None:
        write_csv(rows, csv_path)
    return rows


def run_open(
    *,
    limit: int,
    include_junior: bool = False,
    config_dir: Path | None = None,
    opener=None,
    stdout: TextIO = sys.stdout,
) -> list[str]:
    if limit <= 0:
        return []
    keyword_groups, sources = _load_generation_inputs(config_dir)
    selected_sources = filter_sources(sources, None)
    selected_keywords = _select_keywords(None, keyword_groups, include_junior)
    rows = generate_links(selected_sources, selected_keywords)
    urls = [row.url for row in rows]
    if opener is None:
        opened = open_urls(urls, limit)
    else:
        opened = open_urls(urls, limit, opener=opener)
    if opened:
        for url in opened:
            stdout.write(f"{url}\n")
    return opened


def run_serve(
    *,
    host: str,
    port: int,
    open_browser: bool = True,
    include_junior: bool = False,
    config_dir: Path | None = None,
) -> None:
    serve_app(
        host=host,
        port=port,
        include_junior=include_junior,
        config_dir=config_dir,
        open_browser=open_browser,
    )


def main(argv: list[str] | None = None, *, config_dir: Path | None = None, opener=None, stdout: TextIO = sys.stdout) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "generate":
        run_generate(
            sources_filter=args.sources,
            explicit_keywords=args.keywords,
            csv_path=args.csv_path,
            include_junior=args.include_junior,
            config_dir=config_dir,
            stdout=stdout,
        )
        return 0

    if args.command == "open":
        run_open(
            limit=args.limit,
            include_junior=args.include_junior,
            config_dir=config_dir,
            opener=opener,
            stdout=stdout,
        )
        return 0

    if args.command == "serve":
        run_serve(
            host=args.host,
            port=args.port,
            open_browser=not args.no_browser,
            include_junior=args.include_junior,
            config_dir=config_dir,
        )
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2
