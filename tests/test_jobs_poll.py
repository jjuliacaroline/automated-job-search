from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from automated_job_search import jobs_poll


class JobsPollTests(unittest.TestCase):
    def _write_config(self, config_dir: Path, *, primary: list[str]) -> None:
        (config_dir / "keywords.json").write_text(
            json.dumps({"primary": primary, "junior": ["trainee"]}),
            encoding="utf-8",
        )
        (config_dir / "sources.json").write_text(
            """
            [
              {
                "id": "jobly",
                "name": "Jobly",
                "enabled": true,
                "search_url_template": "https://www.jobly.fi/en/jobs/uusimaa?search={query}"
              },
              {
                "id": "duunitori",
                "name": "Duunitori",
                "enabled": true,
                "search_url_template": "https://duunitori.fi/tyopaikat?alue=Helsinki%3Bespoo%3Bvantaa&haku={query}",
                "query_encoding": "plus"
              }
            ]
            """,
            encoding="utf-8",
        )

    def test_missing_tg_token_raises_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            self._write_config(config_dir, primary=["environmental"])
            with patch.dict(os.environ, {"TG_CHAT": "123"}, clear=True):
                with self.assertRaisesRegex(RuntimeError, "TG_TOKEN"):
                    jobs_poll.run_poll(
                        config_dir=config_dir,
                        fetch_html=lambda url: "",
                        bot_factory=lambda token: object(),
                        send_helper=lambda bot, chat_id, source_label, keyword_label, url: asyncio.sleep(0),
                        sleep_fn=lambda seconds: None,
                    )

    def test_missing_tg_chat_raises_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            self._write_config(config_dir, primary=["environmental"])
            with patch.dict(os.environ, {"TG_TOKEN": "token"}, clear=True):
                with self.assertRaisesRegex(RuntimeError, "TG_CHAT"):
                    jobs_poll.run_poll(
                        config_dir=config_dir,
                        fetch_html=lambda url: "",
                        bot_factory=lambda token: object(),
                        send_helper=lambda bot, chat_id, source_label, keyword_label, url: asyncio.sleep(0),
                        sleep_fn=lambda seconds: None,
                    )

    def test_db_initialization_creates_seen_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "last_seen_urls.sqlite"
            connection = sqlite3.connect(db_path)
            try:
                jobs_poll._ensure_schema(connection)
                rows = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'seen'"
                ).fetchall()
            finally:
                connection.close()
            self.assertEqual(rows, [("seen",)])

    def test_allowlist_expansion_produces_keyword_and_fixed_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            self._write_config(config_dir, primary=["environmental", "sustainability"])
            custom_allowlist = (
                jobs_poll.AllowlistEntry(
                    kind="keyword_template",
                    family="jobly",
                    source_id="jobly",
                    source_name="Jobly",
                ),
                jobs_poll.AllowlistEntry(
                    kind="fixed_category",
                    family="duunitori",
                    source_name="Duunitori",
                    url="https://duunitori.fi/tyopaikat/ala/ymparistotieteen-alan-tehtavat",
                    label="Ympäristötieteen alan tehtävät",
                ),
            )
            with patch.object(jobs_poll, "POLL_ALLOWLIST", custom_allowlist):
                targets = jobs_poll.build_poll_targets(config_dir=config_dir)

            self.assertEqual(
                [(target.source_id, target.keyword, target.url) for target in targets],
                [
                    ("jobly", "environmental", "https://www.jobly.fi/en/jobs/uusimaa?search=environmental"),
                    ("jobly", "sustainability", "https://www.jobly.fi/en/jobs/uusimaa?search=sustainability"),
                    (
                        "duunitori",
                        "Ympäristötieteen alan tehtävät",
                        "https://duunitori.fi/tyopaikat/ala/ymparistotieteen-alan-tehtavat",
                    ),
                ],
            )

    def test_jobly_extractor_returns_absolute_urls_and_dedupes(self) -> None:
        html_text = """
            <html>
              <body>
                <a href="/en/job/example-job-123">Example job</a>
                <a href="/en/job/example-job-123">Duplicate job</a>
                <a href="/en/jobs/enviroment-and-sustainability/uusimaa">Listing</a>
                <a href="/tyopaikka/finnish-example-456">Finnish job</a>
              </body>
            </html>
        """
        urls = jobs_poll.extract_jobly_result_urls(html_text, "https://www.jobly.fi/en/jobs/uusimaa")
        self.assertEqual(
            urls,
            [
                "https://www.jobly.fi/en/job/example-job-123",
                "https://www.jobly.fi/tyopaikka/finnish-example-456",
            ],
        )

    def test_duunitori_extractor_returns_absolute_urls_and_dedupes(self) -> None:
        html_text = """
            <html>
              <body>
                <a href="/tyopaikat/tyo/example-job-123">Example job</a>
                <a href="/tyopaikat/tyo/example-job-123">Duplicate job</a>
                <a href="/tyopaikat/ala/ymparistotieteen-alan-tehtavat">Category</a>
              </body>
            </html>
        """
        urls = jobs_poll.extract_duunitori_result_urls(html_text, "https://duunitori.fi/tyopaikat?haku=example")
        self.assertEqual(urls, ["https://duunitori.fi/tyopaikat/tyo/example-job-123"])

    def test_seen_url_checks_prevent_duplicate_alerts_across_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            db_path = Path(tmpdir) / "last_seen_urls.sqlite"
            self._write_config(config_dir, primary=["environmental"])
            html_text = """
                <html>
                  <body>
                    <a href="/en/job/example-job-123">Example job</a>
                  </body>
                </html>
            """
            sends: list[str] = []

            async def send_helper(bot, chat_id, source_label, keyword_label, url):
                sends.append(url)

            with patch.dict(os.environ, {"TG_TOKEN": "token", "TG_CHAT": "chat"}, clear=True):
                first_count = jobs_poll.run_poll(
                    config_dir=config_dir,
                    db_path=db_path,
                    fetch_html=lambda url: html_text,
                    bot_factory=lambda token: object(),
                    send_helper=send_helper,
                    sleep_fn=lambda seconds: None,
                )
                second_count = jobs_poll.run_poll(
                    config_dir=config_dir,
                    db_path=db_path,
                    fetch_html=lambda url: html_text,
                    bot_factory=lambda token: object(),
                    send_helper=send_helper,
                    sleep_fn=lambda seconds: None,
                )

            self.assertEqual(first_count, 1)
            self.assertEqual(second_count, 0)
            self.assertEqual(sends, ["https://www.jobly.fi/en/job/example-job-123"])

    def test_urls_are_recorded_only_after_successful_send(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            db_path = Path(tmpdir) / "last_seen_urls.sqlite"
            self._write_config(config_dir, primary=["environmental"])
            html_text = """
                <html>
                  <body>
                    <a href="/en/job/example-job-123">Example job</a>
                  </body>
                </html>
            """
            attempts: list[str] = []

            async def failing_send_helper(bot, chat_id, source_label, keyword_label, url):
                attempts.append(url)
                raise RuntimeError("telegram failed")

            async def successful_send_helper(bot, chat_id, source_label, keyword_label, url):
                attempts.append(url)

            with patch.dict(os.environ, {"TG_TOKEN": "token", "TG_CHAT": "chat"}, clear=True):
                first_count = jobs_poll.run_poll(
                    config_dir=config_dir,
                    db_path=db_path,
                    fetch_html=lambda url: html_text,
                    bot_factory=lambda token: object(),
                    send_helper=failing_send_helper,
                    sleep_fn=lambda seconds: None,
                )
                second_count = jobs_poll.run_poll(
                    config_dir=config_dir,
                    db_path=db_path,
                    fetch_html=lambda url: html_text,
                    bot_factory=lambda token: object(),
                    send_helper=successful_send_helper,
                    sleep_fn=lambda seconds: None,
                )

            connection = sqlite3.connect(db_path)
            try:
                rows = connection.execute("SELECT url FROM seen").fetchall()
            finally:
                connection.close()

            self.assertEqual(first_count, 0)
            self.assertEqual(second_count, 1)
            self.assertEqual(attempts, ["https://www.jobly.fi/en/job/example-job-123", "https://www.jobly.fi/en/job/example-job-123"])
            self.assertEqual(rows, [("https://www.jobly.fi/en/job/example-job-123",)])

    def test_failed_fetch_is_skipped_without_stopping_the_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            self._write_config(config_dir, primary=["environmental"])
            custom_allowlist = (
                jobs_poll.AllowlistEntry(
                    kind="keyword_template",
                    family="jobly",
                    source_id="jobly",
                    source_name="Jobly",
                ),
                jobs_poll.AllowlistEntry(
                    kind="fixed_category",
                    family="duunitori",
                    source_name="Duunitori",
                    url="https://duunitori.fi/tyopaikat/ala/ymparistotieteen-alan-tehtavat",
                    label="Ympäristötieteen alan tehtävät",
                ),
            )
            html_text = """
                <html>
                  <body>
                    <a href="/tyopaikat/tyo/example-job-123">Example job</a>
                  </body>
                </html>
            """
            calls: list[str] = []

            def fetch_html(url: str) -> str:
                calls.append(url)
                if "jobly" in url:
                    raise RuntimeError("boom")
                return html_text

            async def send_helper(bot, chat_id, source_label, keyword_label, url):
                calls.append(url)

            with patch.object(jobs_poll, "POLL_ALLOWLIST", custom_allowlist):
                with patch.dict(os.environ, {"TG_TOKEN": "token", "TG_CHAT": "chat"}, clear=True):
                    count = jobs_poll.run_poll(
                        config_dir=config_dir,
                        db_path=Path(tmpdir) / "last_seen_urls.sqlite",
                        fetch_html=fetch_html,
                        bot_factory=lambda token: object(),
                        send_helper=send_helper,
                        sleep_fn=lambda seconds: None,
                    )

            self.assertEqual(count, 1)
            self.assertIn("https://duunitori.fi/tyopaikat/ala/ymparistotieteen-alan-tehtavat", calls)
            self.assertIn("https://duunitori.fi/tyopaikat/tyo/example-job-123", calls)

    def test_request_delay_is_applied_between_fetches_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            self._write_config(config_dir, primary=["environmental"])
            custom_allowlist = (
                jobs_poll.AllowlistEntry(
                    kind="keyword_template",
                    family="jobly",
                    source_id="jobly",
                    source_name="Jobly",
                ),
                jobs_poll.AllowlistEntry(
                    kind="fixed_category",
                    family="duunitori",
                    source_name="Duunitori",
                    url="https://duunitori.fi/tyopaikat/ala/ymparistotieteen-alan-tehtavat",
                    label="Ympäristötieteen alan tehtävät",
                ),
            )
            fetch_calls: list[str] = []
            sleep_calls: list[float] = []

            def fetch_html(url: str) -> str:
                fetch_calls.append(url)
                return "<html><body>No results</body></html>"

            def sleep_fn(seconds: float) -> None:
                sleep_calls.append(seconds)

            with patch.object(jobs_poll, "POLL_ALLOWLIST", custom_allowlist):
                with patch.object(jobs_poll.random, "uniform", return_value=0.75):
                    with patch.dict(
                        os.environ,
                        {
                            "TG_TOKEN": "token",
                            "TG_CHAT": "chat",
                            "POLL_REQUEST_DELAY_SECONDS": "5",
                        },
                        clear=True,
                    ):
                        count = jobs_poll.run_poll(
                            config_dir=config_dir,
                            db_path=Path(tmpdir) / "last_seen_urls.sqlite",
                            fetch_html=fetch_html,
                            bot_factory=lambda token: object(),
                            send_helper=lambda bot, chat_id, source_label, keyword_label, url: asyncio.sleep(0),
                            sleep_fn=sleep_fn,
                        )

            self.assertEqual(count, 0)
            self.assertEqual(
                fetch_calls,
                [
                    "https://www.jobly.fi/en/jobs/uusimaa?search=environmental",
                    "https://duunitori.fi/tyopaikat/ala/ymparistotieteen-alan-tehtavat",
                ],
            )
            self.assertEqual(sleep_calls, [5.75])

    def test_alert_limit_stops_the_run_after_the_cap_is_reached(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            self._write_config(config_dir, primary=["environmental"])
            custom_allowlist = (
                jobs_poll.AllowlistEntry(
                    kind="keyword_template",
                    family="jobly",
                    source_id="jobly",
                    source_name="Jobly",
                ),
                jobs_poll.AllowlistEntry(
                    kind="fixed_category",
                    family="duunitori",
                    source_name="Duunitori",
                    url="https://duunitori.fi/tyopaikat/ala/ymparistotieteen-alan-tehtavat",
                    label="Ympäristötieteen alan tehtävät",
                ),
            )
            fetch_calls: list[str] = []
            sent_urls: list[str] = []
            html_text = """
                <html>
                  <body>
                    <a href="/en/job/example-job-123">Example job</a>
                    <a href="/en/job/example-job-456">Second job</a>
                  </body>
                </html>
            """

            def fetch_html(url: str) -> str:
                fetch_calls.append(url)
                return html_text

            async def send_helper(bot, chat_id, source_label, keyword_label, url):
                sent_urls.append(url)

            with patch.object(jobs_poll, "POLL_ALLOWLIST", custom_allowlist):
                with patch.dict(
                    os.environ,
                    {"TG_TOKEN": "token", "TG_CHAT": "chat", "POLL_MAX_ALERTS_PER_RUN": "1"},
                    clear=True,
                ):
                    count = jobs_poll.run_poll(
                        config_dir=config_dir,
                        db_path=Path(tmpdir) / "last_seen_urls.sqlite",
                        fetch_html=fetch_html,
                        bot_factory=lambda token: object(),
                        send_helper=send_helper,
                        sleep_fn=lambda seconds: None,
                    )

            self.assertEqual(count, 1)
            self.assertEqual(fetch_calls, ["https://www.jobly.fi/en/jobs/uusimaa?search=environmental"])
            self.assertEqual(sent_urls, ["https://www.jobly.fi/en/job/example-job-123"])

    def test_message_format_uses_source_label_and_keyword_label(self) -> None:
        message = jobs_poll.format_alert_message(
            "Jobly",
            "environmental specialist",
            "https://www.jobly.fi/en/job/example-job-123",
        )
        self.assertEqual(
            message,
            "Jobly: New result with keyword <b>environmental specialist</b> → https://www.jobly.fi/en/job/example-job-123",
        )
