from __future__ import annotations

import html
import threading
import webbrowser
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from textwrap import dedent
from typing import Any
from urllib.parse import parse_qs, urlparse

from .config import (
    KeywordGroups,
    SourceDefinition,
    default_config_dir,
    load_default_keyword_groups,
    load_default_sources,
)
from .generation import GeneratedLink, filter_sources, generate_links, normalize_keywords


def _source_section_label(source: SourceDefinition) -> str:
    return source.section_label or "Sources"


def _split_keywords(raw_keyword: str) -> list[str]:
    keywords: list[str] = []
    for part in raw_keyword.replace(",", "\n").splitlines():
        cleaned = part.strip()
        if cleaned:
            keywords.append(cleaned)
    return normalize_keywords(keywords)


def _link_domain(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _render_link_card(row: GeneratedLink) -> str:
    domain = _link_domain(row.url)
    domain_markup = f'<span class="link-domain">{html.escape(domain)}</span>' if domain else ""
    return dedent(
        f"""
        <article class="link-card">
          <div class="link-card-copy">
            <span class="link-label">{html.escape(row.keyword)}</span>
            {domain_markup}
          </div>
          <a class="open-link" href="{html.escape(row.url)}" target="_blank" rel="noreferrer">
            <span>Open</span>
            <svg viewBox="0 0 20 20" aria-hidden="true" focusable="false">
              <path d="M7 5.5h7.5V13m0-7.5L6 14" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"></path>
            </svg>
          </a>
        </article>
        """
    ).strip()


def _page_data(
    *,
    config_dir=None,
    selected_source_ids: list[str] | None = None,
    raw_keywords: str = "",
    include_junior: bool = False,
) -> dict[str, Any]:
    config_root = config_dir or default_config_dir()
    keyword_groups = load_default_keyword_groups(config_root)
    all_sources = load_default_sources(config_root)
    enabled_sources = [source for source in all_sources if source.enabled]
    base_keywords = keyword_groups.primary
    selected_keywords = _split_keywords(raw_keywords) or normalize_keywords(base_keywords)
    if include_junior:
        selected_keywords = normalize_keywords(selected_keywords + keyword_groups.junior)
    sources = filter_sources(enabled_sources, selected_source_ids)
    rows = generate_links(sources, selected_keywords)
    grouped_rows: dict[str, list[GeneratedLink]] = defaultdict(list)
    for row in rows:
        grouped_rows[row.source_id].append(row)
    grouped_sources: dict[str, list[SourceDefinition]] = defaultdict(list)
    section_order: list[str] = []
    for source in enabled_sources:
        section_label = _source_section_label(source)
        if section_label not in grouped_sources:
            section_order.append(section_label)
        grouped_sources[section_label].append(source)
    return {
        "keyword_groups": keyword_groups,
        "enabled_sources": enabled_sources,
        "grouped_sources": dict(grouped_sources),
        "section_order": section_order,
        "keywords": selected_keywords,
        "raw_keywords": raw_keywords,
        "rows": rows,
        "grouped_rows": dict(grouped_rows),
        "selected_source_ids": {source.id for source in sources},
        "include_junior": include_junior,
    }


def render_page(
    *,
    config_dir=None,
    selected_source_ids: list[str] | None = None,
    raw_keywords: str = "",
    include_junior: bool = False,
    error_message: str | None = None,
) -> str:
    data = _page_data(
        config_dir=config_dir,
        selected_source_ids=selected_source_ids,
        raw_keywords=raw_keywords,
        include_junior=include_junior,
    )
    grouped_rows: dict[str, list[GeneratedLink]] = data["grouped_rows"]
    selected_ids: set[str] = data["selected_source_ids"]
    grouped_sources: dict[str, list[SourceDefinition]] = data["grouped_sources"]
    section_order: list[str] = data["section_order"]
    keywords: list[str] = data["keywords"]
    escaped_keywords = html.escape(data["raw_keywords"])
    keyword_groups: KeywordGroups = data["keyword_groups"]
    primary_keywords_preview = ", ".join(keyword_groups.primary[:6])
    junior_count = len(keyword_groups.junior)
    result_sections: list[str] = []
    source_option_sections: list[str] = []

    for section_label in section_order:
        section_sources = grouped_sources.get(section_label, [])
        section_cards: list[str] = []
        section_options: list[str] = []
        for source in section_sources:
            section_options.append(
                f'<label class="source-option"><input type="checkbox" name="source" value="{html.escape(source.id)}"'
                f' {"checked" if source.id in selected_ids else ""}>'
                f'<span>{html.escape(source.name)}</span></label>'
            )
            if source.id not in selected_ids:
                continue
            source_rows = grouped_rows.get(source.id, [])
            links_markup = "\n".join(_render_link_card(row) for row in source_rows)
            notes = f'<p class="source-notes">{html.escape(source.notes)}</p>' if source.notes else ""
            section_cards.append(
                dedent(
                    f"""
                    <details class="source-accordion" open>
                      <summary>
                        <span class="accordion-title">{html.escape(source.name)}</span>
                        <span class="accordion-count">{len(source_rows)} links</span>
                      </summary>
                      {notes}
                      <div class="link-grid">
                        {links_markup}
                      </div>
                    </details>
                    """
                ).strip()
            )
        if section_cards:
            result_sections.append(
                dedent(
                    f"""
                    <section class="result-section">
                      <p class="section-title">{html.escape(section_label)}</p>
                      <div class="accordion-stack">
                        {"\n".join(section_cards)}
                      </div>
                    </section>
                    """
                ).strip()
            )
        if section_options:
            source_option_sections.append(
                dedent(
                    f"""
                    <section class="source-section">
                      <p class="section-title">{html.escape(section_label)}</p>
                      <div class="source-grid">
                        {"\n".join(section_options)}
                      </div>
                    </section>
                    """
                ).strip()
            )

    error_banner = f'<div class="error-banner">{html.escape(error_message)}</div>' if error_message else ""
    selected_count = len(selected_ids)
    page_body = (
        "\n".join(result_sections)
        if result_sections
        else '<section class="empty-state">No links matched the current filters.</section>'
    )
    source_options = "\n".join(source_option_sections)

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
              --primary: #005C4D;
              --accent: #0F766E;
              --surface: #F7F1E6;
              --surface-strong: #EFE5D2;
              --bg: #F5F0E7;
              --ink: #18302B;
              --muted: #607169;
              --line: rgba(24, 48, 43, 0.12);
              --shadow: 0 18px 45px rgba(18, 43, 38, 0.08);
            }}
            * {{ box-sizing: border-box; }}
            body {{
              margin: 0;
              font-family: "Inter", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
              color: var(--ink);
              background:
                radial-gradient(circle at top left, rgba(0, 92, 77, 0.12), transparent 30%),
                linear-gradient(180deg, #fcfaf6 0%, var(--bg) 100%);
            }}
            h1, h2, .section-title, .accordion-title {{
              font-family: Georgia, "Times New Roman", serif;
            }}
            a {{ color: var(--accent); }}
            .shell {{
              max-width: 1200px;
              margin: 0 auto;
              padding: 20px 20px 40px;
            }}
            .hero {{
              padding: 18px 20px 20px;
              border-radius: 0;
              background: var(--primary);
              color: white;
            }}
            .hero-top {{
              display: flex;
              align-items: flex-start;
              justify-content: space-between;
              gap: 16px;
            }}
            .hero h1 {{
              margin: 0;
              font-size: clamp(2.1rem, 5vw, 4.4rem);
              line-height: 0.95;
              letter-spacing: -0.05em;
            }}
            .hero-copy {{
              max-width: 72ch;
              margin: 12px 0 0;
              color: rgba(255, 255, 255, 0.82);
              font-size: 1.02rem;
            }}
            .stats {{
              display: flex;
              flex-wrap: nowrap;
              gap: 12px;
              margin-top: 14px;
              overflow-x: auto;
              padding-bottom: 2px;
            }}
            .stat {{
              padding: 10px 14px;
              border-radius: 999px;
              background: rgba(255, 255, 255, 0.14);
              border: 1px solid rgba(255, 255, 255, 0.16);
              color: white;
              font-size: 0.95rem;
              white-space: nowrap;
            }}
            .menu-toggle {{
              display: none;
              align-items: center;
              gap: 8px;
              padding: 10px 14px;
              border-radius: 999px;
              border: 1px solid rgba(255, 255, 255, 0.18);
              color: white;
              background: rgba(255, 255, 255, 0.08);
            }}
            .menu-toggle svg {{
              width: 18px;
              height: 18px;
            }}
            .layout {{
              display: grid;
              grid-template-columns: 320px minmax(0, 1fr);
              gap: 20px;
              margin-top: 18px;
            }}
            .panel {{
              background: var(--surface);
              border: 1px solid var(--line);
              border-radius: 24px;
              box-shadow: var(--shadow);
            }}
            .sidebar {{
              position: sticky;
              top: 16px;
              align-self: start;
              display: grid;
              gap: 14px;
            }}
            .sidebar-form {{
              display: grid;
              gap: 14px;
            }}
            .controls {{
              padding: 18px;
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
              font-weight: 600;
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
            .toggle-row {{
              display: flex;
              align-items: center;
              gap: 10px;
              margin-top: 12px;
              padding: 12px 14px;
              border-radius: 16px;
              background: rgba(255, 255, 255, 0.65);
              border: 1px solid var(--line);
            }}
            .control-card {{
              padding: 16px;
              border-radius: 20px;
              background: var(--surface-strong);
              border: 1px solid rgba(24, 48, 43, 0.08);
            }}
            .control-card + .control-card {{
              margin-top: 14px;
            }}
            .source-grid {{
              display: grid;
              gap: 10px;
            }}
            .source-section + .source-section {{
              margin-top: 18px;
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
              margin-top: 6px;
              position: sticky;
              bottom: 0;
              padding-top: 12px;
              background: linear-gradient(180deg, rgba(247, 241, 230, 0), rgba(247, 241, 230, 0.92) 18px, rgba(247, 241, 230, 0.98));
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
            .result-section {{
              display: grid;
              gap: 12px;
            }}
            .accordion-stack {{
              display: grid;
              gap: 12px;
            }}
            .source-accordion {{
              border-radius: 20px;
              background: white;
              border: 1px solid var(--line);
              overflow: clip;
            }}
            .source-accordion summary {{
              list-style: none;
              display: flex;
              align-items: center;
              justify-content: space-between;
              gap: 14px;
              padding: 16px 18px;
              cursor: pointer;
            }}
            .source-accordion summary::-webkit-details-marker {{
              display: none;
            }}
            .accordion-title {{
              margin: 0;
              font-size: 1.22rem;
              line-height: 1.1;
              font-weight: 700;
            }}
            .accordion-count {{
              white-space: nowrap;
              border-radius: 999px;
              padding: 7px 11px;
              background: var(--surface);
              color: var(--accent);
              font-size: 0.88rem;
              font-weight: 600;
            }}
            .source-notes {{
              margin: 0 18px 10px;
              color: var(--muted);
            }}
            .link-grid {{
              display: grid;
              gap: 10px;
              padding: 0 18px 18px;
            }}
            .link-card {{
              display: flex;
              align-items: center;
              justify-content: space-between;
              gap: 14px;
              padding: 12px 14px;
              border-radius: 16px;
              background: #F8F6F1;
              border: 1px solid rgba(24, 48, 43, 0.08);
            }}
            .link-card-copy {{
              min-width: 0;
            }}
            .link-label {{
              display: inline-block;
              color: var(--ink);
              text-decoration: none;
              font-family: Georgia, "Times New Roman", serif;
              font-size: 1.02rem;
              font-weight: 700;
              line-height: 1.2;
            }}
            .link-label:hover {{
              color: var(--accent);
            }}
            .link-domain {{
              display: block;
              margin-top: 4px;
              color: var(--muted);
              font-size: 0.78rem;
              font-variant-caps: all-small-caps;
              letter-spacing: 0.1em;
            }}
            .open-link {{
              display: inline-flex;
              align-items: center;
              gap: 6px;
              flex: 0 0 auto;
              padding: 10px 14px;
              border-radius: 999px;
              background: var(--accent);
              color: white;
              text-decoration: none;
              font-size: 0.92rem;
              font-weight: 600;
            }}
            .open-link svg {{
              width: 16px;
              height: 16px;
            }}
            .empty-state {{
              padding: 24px;
              border-radius: 18px;
              background: white;
              border: 1px dashed var(--line);
              color: var(--muted);
            }}
            @media (max-width: 959px) {{
              .menu-toggle {{
                display: inline-flex;
              }}
              .layout {{
                grid-template-columns: 1fr;
              }}
              .sidebar {{
                position: static;
                display: none;
              }}
              body.sidebar-open .sidebar {{
                display: grid;
              }}
              .hero-top {{
                align-items: center;
              }}
              .hero-copy {{
                max-width: none;
              }}
              .source-accordion summary {{
                align-items: flex-start;
                flex-direction: column;
              }}
              .link-card {{
                align-items: flex-start;
                flex-direction: column;
              }}
              .open-link {{
                align-self: flex-start;
              }}
            }}
            @media (max-width: 640px) {{
              .shell {{
                padding-inline: 12px;
              }}
              .hero {{
                padding-inline: 14px;
              }}
              .controls, .results {{
                padding: 16px;
              }}
              .actions {{
                flex-direction: row;
              }}
            }}
          </style>
        </head>
        <body>
          <main class="shell">
            <section class="hero">
              <div class="hero-top">
                <h1>Finland<br>Environmental Jobs</h1>
                <button class="menu-toggle" type="button" aria-controls="sidebar" aria-expanded="false">
                  <svg viewBox="0 0 20 20" aria-hidden="true" focusable="false">
                    <path d="M3 5h14M3 10h14M3 15h14" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"></path>
                  </svg>
                  <span>Filters</span>
                </button>
              </div>
              <p class="hero-copy">
                A browser view over the existing link generator. It still produces public search URLs, but the results are easier to scan, filter, and open in new tabs.
              </p>
              <div class="stats">
                <span class="stat">{len(data["rows"])} clickable links</span>
                <span class="stat">{selected_count} sources selected</span>
                <span class="stat">{len(keywords)} keywords active</span>
              </div>
            </section>
            <div class="layout">
              <aside class="sidebar" id="sidebar">
                <form method="get" action="/" class="sidebar-form">
                  <section class="control-card panel controls">
                    <p class="section-title">Keywords</p>
                    <textarea name="keywords" placeholder="One keyword per line">{escaped_keywords}</textarea>
                    <p class="hint">Leave blank to use defaults. Main keywords start with: {html.escape(primary_keywords_preview)}</p>
                    <label class="toggle-row">
                      <input type="checkbox" name="include_junior" {"checked" if include_junior else ""}>
                      <span>Include junior keywords as an extra group ({junior_count})</span>
                    </label>
                  </section>
                  <section class="control-card panel controls">
                    <p class="section-title">Sources</p>
                    {source_options}
                  </section>
                  <div class="actions">
                    <button type="submit">Refresh</button>
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
          <script>
            (function() {{
              const mq = window.matchMedia("(max-width: 959px)");
              const body = document.body;
              const toggle = document.querySelector(".menu-toggle");
              const accordions = Array.from(document.querySelectorAll(".source-accordion"));

              function syncLayout() {{
                const isMobile = mq.matches;
                if (isMobile) {{
                  accordions.forEach((accordion) => {{
                    accordion.open = false;
                  }});
                  if (toggle) {{
                    toggle.setAttribute("aria-expanded", String(body.classList.contains("sidebar-open")));
                  }}
                }} else {{
                  body.classList.remove("sidebar-open");
                  accordions.forEach((accordion) => {{
                    accordion.open = true;
                  }});
                  if (toggle) {{
                    toggle.setAttribute("aria-expanded", "false");
                  }}
                }}
              }}

              if (toggle) {{
                toggle.addEventListener("click", () => {{
                  if (!mq.matches) {{
                    return;
                  }}
                  const nextOpen = !body.classList.contains("sidebar-open");
                  body.classList.toggle("sidebar-open", nextOpen);
                  toggle.setAttribute("aria-expanded", String(nextOpen));
                }});
              }}

              if (mq.addEventListener) {{
                mq.addEventListener("change", syncLayout);
              }} else if (mq.addListener) {{
                mq.addListener(syncLayout);
              }}
              syncLayout();
            }})();
          </script>
        </body>
        </html>
        """
    ).strip()


def create_handler(config_dir=None, include_junior: bool = False):
    class JobLinksHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path != "/":
                self.send_error(404, "Not Found")
                return

            params = parse_qs(parsed.query)
            selected_source_ids = params.get("source")
            raw_keywords = params.get("keywords", [""])[0]
            include_junior = "include_junior" in params
            error_message = None
            try:
                page = render_page(
                    config_dir=config_dir,
                    selected_source_ids=selected_source_ids,
                    raw_keywords=raw_keywords,
                    include_junior=include_junior,
                )
            except ValueError as exc:
                error_message = str(exc)
                page = render_page(
                    config_dir=config_dir,
                    selected_source_ids=None,
                    raw_keywords=raw_keywords,
                    include_junior=include_junior,
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


def serve_app(
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    config_dir=None,
    include_junior: bool = False,
    open_browser: bool = True,
) -> None:
    server = ThreadingHTTPServer((host, port), create_handler(config_dir=config_dir, include_junior=include_junior))
    url = f"http://{host}:{port}"
    print(f"Serving job links UI at {url}")
    if open_browser:
        threading.Timer(0.3, lambda: webbrowser.open_new_tab(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
