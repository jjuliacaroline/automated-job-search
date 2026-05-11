# Automated Job Search

Small Python CLI for generating public job-board search URLs for environmental science and sustainability roles in Finland.

This MVP intentionally stops at link generation. It does not scrape listings, fetch job pages, or automate browsers beyond an explicit `open` command that opens a limited number of already-generated URLs.

## Install

From the repository root:

```bash
python3 -m pip install .
```

For editable development installs:

```bash
python3 -m pip install -e .
```

After installation, the console script is available as:

```bash
automated-job-search generate
```

## Usage

Generate search URLs using the default keywords and sources:

```bash
automated-job-search generate
```

Filter to one or more sources:

```bash
automated-job-search generate --source jobly --source duunitori
```

Use explicit keywords instead of the defaults:

```bash
automated-job-search generate --keyword ympäristöasiantuntija --keyword trainee
```

Export to CSV:

```bash
automated-job-search generate --csv links.csv
```

Open up to a small number of generated links:

```bash
automated-job-search open --limit 5
```

## Configuration

Editable config files live in `config/`:

- [`config/keywords.json`](config/keywords.json) contains the default keyword list.
- [`config/sources.json`](config/sources.json) contains the source templates.

Sources are currently:

- Jobly
- Duunitori
- Kuntarekry

If you want to change keywords or add/remove sources, edit those JSON files instead of the Python modules.

## Development

Run tests with:

```bash
python3 -m unittest discover -s tests -v
```

The codebase uses only the Python standard library.

