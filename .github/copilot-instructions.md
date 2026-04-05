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

- **`io.py`** — Read/write `.dic` and `.dicx` dictionary files, merge dictionaries, fetch remote dictionaries via Pooch. All dictionary DataFrames are validated through a Pandera schema (`dx_schema`) that enforces: lowercase string index named "DicTerm", binary int64 values, sorted columns named "Category".

- **`count.py`** — Pure-Python LIWC-style word counting (no LIWC-22 needed). Uses scikit-learn's `CountVectorizer`. Dictionary wildcards (e.g., `abandon*`) are expanded against the actual corpus vocabulary before counting.

- **`liwc22.py`** — CLI wrapper around `liwc-22-cli`. Uses a data-driven design: all arguments defined once in `ARG_CATALOGUE`, modes defined in `MODE_DEFS`. Also exposes `cli()` for Python-level invocation. The `liwca` console script entry point is `main()` in this module.

Supporting module `_catalogue.py` defines `DictInfo` metadata and the `CATALOGUE` dict (single source of truth for all registered dictionaries), plus reader functions for non-standard remote dictionary formats.

## Code Style

- Ruff: line length 100, target Python 3.14, rules `E, F, I, W, C90, NPY201`
- Docstrings: NumPy convention
- Formatting: double quotes, LF line endings
- Always use `uv` when running Python scripts or installing dependencies
