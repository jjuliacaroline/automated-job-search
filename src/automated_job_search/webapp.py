from __future__ import annotations

import html
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from textwrap import dedent
from typing import Any
from urllib.parse import parse_qs, urlparse

from .config import SourceDefinition, default_config_dir, load_default_keywords, load_default_sources
from .generation import GeneratedLink, filter_sources, generate_links, normalize_keywords


def _split_keywords(raw_keyword: str) -> list[str]:
    keywords: list[str] = []
    for part in raw_keyword.replace(",", "\n").splitlines():
        cleaned = part.strip()
        if cleaned:
            keywords.append(cleaned)
    return normalize_keywords(keywords)


def _page_data(
    *,
    config_dir=None,
    selected_source_ids: list[str] | None = None,
    raw_keywords: str = "",
) -> dict[str, Any]:
    config_root = config_dir or default_config_dir()
    default_keywords = load_default_keywords(config_root)
    all_sources = load_default_sources(config_root)
    enabled_sources = [source for source in all_sources if source.enabled]
    keywords = _split_keywords(raw_keywords) or normalize_keywords(default_keywords)
    sources = filter_sources(enabled_sources, selected_source_ids)
    rows = generate_links(sources, keywords)
    grouped_rows: dict[str, list[GeneratedLink]] = defaultdict(list)
    for row in rows:
        grouped_rows[row.source_id].append(row)
    return {
        "default_keywords": default_keywords,
        "enabled_sources": enabled_sources,
        "keywords": keywords,
        "raw_keywords": raw_keywords,
        "rows": rows,
        "grouped_rows": dict(grouped_rows),
        "selected_source_ids": {source.id for source in sources},
    }


def render_page(
    *,
    config_dir=None,
    selected_source_ids: list[str] | None = None,
    raw_keywords: str = "",
    error_message: str | None = None,
) -> str:
    data = _page_data(
        config_dir=config_dir,
        selected_source_ids=selected_source_ids,
        raw_keywords=raw_keywords,
    )
    enabled_sources: list[SourceDefinition] = data["enabled_sources"]
    grouped_rows: dict[str, list[GeneratedLink]] = data["grouped_rows"]
    selected_ids: set[str] = data["selected_source_ids"]
    keywords: list[str] = data["keywords"]
    escaped_keywords = html.escape(data["raw_keywords"])
    default_keywords_preview = ", ".join(data["default_keywords"][:6])
    cards: list[str] = []

    for source in enabled_sources:
        if source.id not in selected_ids:
            continue
        source_rows = grouped_rows.get(source.id, [])
        links_markup = "\n".join(
            (
                f'<li><a href="{html.escape(row.url)}" target="_blank" rel="noreferrer">{html.escape(row.keyword)}</a>'
                f'<span>{html.escape(row.url)}</span></li>'
            )
            for row in source_rows
        )
        notes = f'<p class="source-notes">{html.escape(source.notes)}</p>' if source.notes else ""
        cards.append(
            dedent(
                f"""
                <section class="result-card">
                  <div class="card-header">
                    <div>
                      <p class="eyebrow">{html.escape(source.id)}</p>
                      <h2>{html.escape(source.name)}</h2>
                    </div>
                    <span class="pill">{len(source_rows)} links</span>
                  </div>
                  {notes}
                  <ul class="link-list">
                    {links_markup}
                  </ul>
                </section>
                """
            ).strip()
        )

    source_options = "\n".join(
        (
            f'<label class="source-option"><input type="checkbox" name="source" value="{html.escape(source.id)}"'
            f' {"checked" if source.id in selected_ids else ""}>'
            f'<span>{html.escape(source.name)}</span></label>'
        )
        for source in enabled_sources
    )
    error_banner = f'<div class="error-banner">{html.escape(error_message)}</div>' if error_message else ""
    selected_count = len(selected_ids)
    page_body = "\n".join(cards) if cards else '<section class="empty-state">No links matched the current filters.</section>'

    return dedent(
        f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>Finland Environmental Jobs</title>
          <style>
            :root {{
              --bg: #f3efe6;
              --panel: rgba(255, 252, 247, 0.92);
              --ink: #1f3027;
              --muted: #617166;
              --accent: #146356;
              --accent-soft: #d7efe5;
              --line: rgba(31, 48, 39, 0.12);
              --shadow: 0 18px 45px rgba(20, 43, 31, 0.08);
            }}
            * {{ box-sizing: border-box; }}
            body {{
              margin: 0;
              font-family: Georgia, "Times New Roman", serif;
              color: var(--ink);
              background:
                radial-gradient(circle at top left, rgba(20, 99, 86, 0.12), transparent 30%),
                linear-gradient(180deg, #fcfaf6 0%, var(--bg) 100%);
            }}
            a {{ color: var(--accent); }}
            .shell {{
              max-width: 1200px;
              margin: 0 auto;
              padding: 32px 20px 48px;
            }}
            .hero {{
              padding: 28px;
              border-radius: 28px;
              background: linear-gradient(135deg, rgba(255, 252, 247, 0.95), rgba(222, 241, 230, 0.92));
              box-shadow: var(--shadow);
              border: 1px solid rgba(20, 99, 86, 0.12);
            }}
            .hero h1 {{
              margin: 0;
              font-size: clamp(2.2rem, 5vw, 4.5rem);
              line-height: 0.95;
              letter-spacing: -0.05em;
            }}
            .hero p {{
              max-width: 70ch;
              margin: 14px 0 0;
              color: var(--muted);
              font-size: 1.02rem;
            }}
            .stats {{
              display: flex;
              flex-wrap: wrap;
              gap: 12px;
              margin-top: 18px;
            }}
            .stat {{
              padding: 10px 14px;
              border-radius: 999px;
              background: rgba(255, 255, 255, 0.7);
              border: 1px solid var(--line);
              font-size: 0.95rem;
            }}
            .layout {{
              display: grid;
              grid-template-columns: 320px minmax(0, 1fr);
              gap: 20px;
              margin-top: 22px;
            }}
            .panel {{
              background: var(--panel);
              border: 1px solid var(--line);
              border-radius: 24px;
              box-shadow: var(--shadow);
            }}
            .controls {{
              padding: 20px;
              position: sticky;
              top: 20px;
              align-self: start;
            }}
            .results {{
              padding: 20px;
            }}
            .section-title {{
              margin: 0 0 12px;
              font-size: 0.86rem;
              text-transform: uppercase;
              letter-spacing: 0.14em;
              color: var(--muted);
            }}
            textarea {{
              width: 100%;
              min-height: 180px;
              padding: 14px;
              border-radius: 18px;
              border: 1px solid var(--line);
              background: white;
              color: var(--ink);
              font: inherit;
              resize: vertical;
            }}
            .hint {{
              margin: 10px 0 0;
              color: var(--muted);
              font-size: 0.92rem;
            }}
            .source-grid {{
              display: grid;
              gap: 10px;
              margin-top: 10px;
            }}
            .source-option {{
              display: flex;
              align-items: center;
              gap: 10px;
              padding: 12px 14px;
              border-radius: 16px;
              background: white;
              border: 1px solid var(--line);
            }}
            .source-option input {{
              accent-color: var(--accent);
            }}
            .actions {{
              display: flex;
              gap: 10px;
              margin-top: 18px;
            }}
            button {{
              border: 0;
              border-radius: 999px;
              padding: 12px 18px;
              font: inherit;
              cursor: pointer;
              background: var(--accent);
              color: white;
            }}
            .ghost-link {{
              display: inline-flex;
              align-items: center;
              justify-content: center;
              text-decoration: none;
              padding: 12px 18px;
              border-radius: 999px;
              border: 1px solid var(--line);
              color: var(--ink);
            }}
            .error-banner {{
              margin-bottom: 14px;
              padding: 12px 14px;
              border-radius: 16px;
              background: #fff0ec;
              color: #8d2a12;
              border: 1px solid rgba(141, 42, 18, 0.15);
            }}
            .result-grid {{
              display: grid;
              gap: 16px;
            }}
            .result-card {{
              padding: 18px;
              border-radius: 20px;
              background: white;
              border: 1px solid var(--line);
            }}
            .card-header {{
              display: flex;
              justify-content: space-between;
              gap: 12px;
              align-items: start;
            }}
            .card-header h2 {{
              margin: 2px 0 0;
              font-size: 1.5rem;
            }}
            .eyebrow {{
              margin: 0;
              text-transform: uppercase;
              letter-spacing: 0.12em;
              font-size: 0.78rem;
              color: var(--muted);
            }}
            .pill {{
              white-space: nowrap;
              border-radius: 999px;
              padding: 8px 12px;
              background: var(--accent-soft);
              color: var(--accent);
              font-size: 0.9rem;
            }}
            .source-notes {{
              margin: 12px 0 0;
              color: var(--muted);
            }}
            .link-list {{
              list-style: none;
              margin: 16px 0 0;
              padding: 0;
              display: grid;
              gap: 10px;
            }}
            .link-list li {{
              padding: 12px 14px;
              border-radius: 16px;
              background: #f8f6f1;
              border: 1px solid rgba(31, 48, 39, 0.08);
            }}
            .link-list a {{
              text-decoration: none;
              font-weight: 700;
              font-size: 1rem;
            }}
            .link-list span {{
              display: block;
              margin-top: 6px;
              color: var(--muted);
              font-size: 0.9rem;
              word-break: break-all;
            }}
            .empty-state {{
              padding: 24px;
              border-radius: 18px;
              background: white;
              border: 1px dashed var(--line);
              color: var(--muted);
            }}
            @media (max-width: 920px) {{
              .layout {{
                grid-template-columns: 1fr;
              }}
              .controls {{
                position: static;
              }}
            }}
          </style>
        </head>
        <body>
          <main class="shell">
            <section class="hero">
              <h1>Finland<br>Environmental Jobs</h1>
              <p>
                A browser view over the existing link generator. It still produces public search URLs, but the results are easier to scan, filter, and open in new tabs.
              </p>
              <div class="stats">
                <span class="stat">{len(data["rows"])} clickable links</span>
                <span class="stat">{selected_count} sources selected</span>
                <span class="stat">{len(keywords)} keywords active</span>
              </div>
            </section>
            <div class="layout">
              <aside class="panel controls">
                <form method="get" action="/">
                  <p class="section-title">Keywords</p>
                  <textarea name="keywords" placeholder="One keyword per line">{escaped_keywords}</textarea>
                  <p class="hint">Leave blank to use defaults. Current defaults start with: {html.escape(default_keywords_preview)}</p>
                  <p class="section-title" style="margin-top: 22px;">Sources</p>
                  <div class="source-grid">
                    {source_options}
                  </div>
                  <div class="actions">
                    <button type="submit">Refresh Results</button>
                    <a class="ghost-link" href="/">Reset</a>
                  </div>
                </form>
              </aside>
              <section class="panel results">
                {error_banner}
                <div class="result-grid">
                  {page_body}
                </div>
              </section>
            </div>
          </main>
        </body>
        </html>
        """
    ).strip()


def create_handler(config_dir=None):
    class JobLinksHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path != "/":
                self.send_error(404, "Not Found")
                return

            params = parse_qs(parsed.query)
            selected_source_ids = params.get("source")
            raw_keywords = params.get("keywords", [""])[0]
            error_message = None
            try:
                page = render_page(
                    config_dir=config_dir,
                    selected_source_ids=selected_source_ids,
                    raw_keywords=raw_keywords,
                )
            except ValueError as exc:
                error_message = str(exc)
                page = render_page(
                    config_dir=config_dir,
                    selected_source_ids=None,
                    raw_keywords=raw_keywords,
                    error_message=error_message,
                )

            payload = page.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            return

    return JobLinksHandler


def serve_app(*, host: str = "127.0.0.1", port: int = 8000, config_dir=None) -> None:
    server = ThreadingHTTPServer((host, port), create_handler(config_dir=config_dir))
    print(f"Serving job links UI at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
