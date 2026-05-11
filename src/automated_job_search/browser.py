from __future__ import annotations

import webbrowser
from collections.abc import Callable, Iterable


def open_urls(
    urls: Iterable[str],
    limit: int,
    opener: Callable[[str], bool] = webbrowser.open_new_tab,
) -> list[str]:
    if limit <= 0:
        return []
    opened: list[str] = []
    for url in urls:
        if len(opened) >= limit:
            break
        opener(url)
        opened.append(url)
    return opened
