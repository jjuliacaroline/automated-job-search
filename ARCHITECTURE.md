# Architecture

This MVP is intentionally small.

## Design Goals

- Generate public search URLs for a curated set of Finnish job boards.
- Keep the core logic config-driven so keywords and sources can be edited without changing Python code.
- Stop at link generation. No scraping, no listing persistence, no browser automation beyond the explicit `open` command.

## Layout

- `src/automated_job_search/cli.py`: argument parsing and command dispatch.
- `src/automated_job_search/config.py`: JSON loading and validation for keywords and sources.
- `src/automated_job_search/generation.py`: keyword/source combination and URL construction.
- `src/automated_job_search/csv_export.py`: CSV export helpers.
- `src/automated_job_search/browser.py`: conservative URL opening helper built on the standard library.
- `config/keywords.json`: ordered default keyword list.
- `config/sources.json`: ordered source definitions.

## Configuration Model

Keywords and sources live in editable JSON files. The CLI loads them at runtime, which keeps the job-board catalog easy to change without touching the generator.

The keyword config is split into two groups:

- `primary`: default search terms
- `junior`: an optional group that only appears when explicitly enabled

Sources use a minimal schema:

- `id`
- `name`
- `enabled`
- optional `section_label` for grouping in the browser UI
- `search_url_template` or `base_url`
- optional `notes`

Templates use a single `{query}` placeholder. The generator percent-encodes the keyword before substitution so URLs remain safe for spaces and Finnish characters.

## CLI Behavior

- `generate` prints the generated rows and can export them to CSV.
- `generate --source ...` limits output to one or more source ids.
- `generate --keyword ...` uses explicit keywords instead of the defaults.
- `generate --include-junior` appends the optional junior group.
- `serve` exposes the same split in the browser UI with a dedicated junior checkbox.
- `open --limit N` opens at most `N` already generated URLs and never exceeds the requested limit.

## Why It Stops Here

This repository is designed as an MVP for search-link generation, not a crawler or job aggregation service. Stopping at URLs keeps the code predictable, avoids site-specific breakage, and avoids any need for scraping logic, automated browsing, or anti-bot workarounds.
