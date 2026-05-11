# Agent Instructions

Scope for this repository:

- Keep the implementation focused on generating public job-board search links for Finland-based environmental science and sustainability roles.
- Do not add scraping, browser automation beyond the explicit `open` command, login handling, CAPTCHA bypassing, robots circumvention, or any network fetch layer that tries to discover listings.
- Treat config files under `config/` as the editable source of truth for keywords and source templates. Update code only when the config schema changes.
- Prefer small, reviewable edits. If a source cannot be represented cleanly as a stable public search URL, leave it out rather than approximating it with scraping logic.

Source additions:

- Only add sources that expose a stable public search or category URL.
- Keep templates generic and minimal. Use one encoded keyword placeholder and avoid source-specific parsing logic.
- Validate any new source against the current public page structure before committing it.

Keyword updates:

- Keep keywords ordered and concise.
- Include both environmental/sustainability terms and junior-friendly terms when updating the default list.
- If a keyword becomes noisy or too broad, remove it from the JSON config instead of hard-coding exceptions.

Implementation expectations:

- Preserve the CLI-first design.
- Keep dependencies minimal. Standard library should remain the default choice.
- Maintain test coverage for config loading, URL generation, source filtering, CSV export, and basic CLI behavior.

