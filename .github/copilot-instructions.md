# Copilot Instructions

This file provides guidance to GitHub Copilot when working with code in this repository.

## Project Overview

LIWCA is a Python helper library for working with [LIWC](https://liwc.app) dictionaries. It provides pure-Python word counting, dictionary file I/O (`.dic`/`.dicx`), remote dictionary fetching, and a CLI wrapper around `liwc-22-cli`.

## Commands

```bash
# Install in development mode
uv pip install -e ".[dev]"

# Run all tests with coverage
uv run pytest tests/ --cov=liwca --cov-report=term-missing

# Run a single test file or test
uv run pytest tests/test_count.py
uv run pytest tests/test_count.py::test_name

# Lint and format
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Type checking
uv run mypy
```

## Architecture

Three main modules under `src/liwca/`:

- **`io.py`** - Read/write `.dic` and `.dicx` dictionary files, merge dictionaries, fetch remote dictionaries via Pooch. All dictionary DataFrames are validated through a Pandera schema (`dx_schema`) that enforces: lowercase string index named "DicTerm", binary int8 values, sorted columns named "Category".

- **`count.py`** - Pure-Python LIWC-style word counting (no LIWC-22 needed). Uses scikit-learn's `CountVectorizer`. Dictionary wildcards (e.g., `abandon*`) are expanded against the actual corpus vocabulary before counting.

- **`liwc22.py`** - Python wrapper around `liwc-22-cli` via the `Liwc22` class. Hoisted constructor args (those applying to ≥5 of the 7 modes) plus execution-control flags (`auto_open`, `use_gui`, `dry_run`) are set once; the seven per-mode methods (`wc`, `freq`, `mem`, `context`, `arc`, `ct`, `lsm`) take only mode-specific kwargs. Each method accepts `input` as either a filepath (`str`) or a `pandas.DataFrame` (written to a temp CSV, fed to the CLI, then removed), and returns the `output` path on success (`None` for dry-run; `subprocess.CalledProcessError` on CLI failure). `wc`-mode output is reshaped in place via `wc_output_schema` (Row ID renamed to source column, constant Segment dropped, column axis named `Category`). `FLAG_BY_DEST` maps each dest to its CLI flag; flag-category frozensets drive command assembly — `BOOL_FLAGS` (value-less), `YES_NO_FLAGS` (`bool` → `yes`/`no`), `ONE_ZERO_FLAGS` (`bool` → `1`/`0`), `LIST_FLAGS` (`Iterable[str]` → comma-joined), plus `COLUMN_FLAGS` and `COLUMN_LIST_FLAGS` (0-based int or column-name str → 1-based int, resolved by `_resolve_columns`). `MODE_GLOBALS` filters which hoisted args apply to each mode. Supports use as a context manager.

Supporting module `_catalogue.py` loads `data/registry.json` (the single source of truth for all dictionary metadata and download info), builds the `CATALOGUE` dict of `DictInfo` objects at import time, and defines reader functions for non-standard remote dictionary formats. Supports versioned dictionaries.

## Code Style

- Ruff: line length 100, target Python 3.14, rules `E, F, I, W, C90, NPY201`
- Docstrings: NumPy convention
- Formatting: double quotes, LF line endings
- Always use `uv` when running Python scripts or installing dependencies
