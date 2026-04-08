# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

- **`io.py`** — Read/write `.dic` and `.dicx` dictionary files, merge dictionaries, fetch remote dictionaries via Pooch. All dictionary DataFrames are validated through a Pandera schema (`dx_schema`) that enforces: lowercase string index named "DicTerm", binary int8 values, sorted columns named "Category".

- **`count.py`** — Pure-Python LIWC-style word counting (no LIWC-22 needed). Uses scikit-learn's `CountVectorizer`. Dictionary wildcards (e.g., `abandon*`) are expanded against the actual corpus vocabulary before counting.

- **`liwc22.py`** — CLI wrapper around `liwc-22-cli`. Uses a data-driven design: all arguments defined once in `ARG_CATALOGUE`, modes defined in `MODE_DEFS`. Also exposes `cli()` for Python-level invocation. The `liwca` console script entry point is `main()` in this module.

Supporting module `_catalogue.py` loads `data/registry.json` (the single source of truth for all dictionary metadata and download info), builds the `CATALOGUE` dict of `DictInfo` objects at import time, and defines reader functions for non-standard remote dictionary formats. Supports versioned dictionaries.

## LIWC Domain Context

LIWC (Linguistic Inquiry and Word Count) is a dictionary-based text analysis method. Texts are scored by counting how many words fall into each psychological/linguistic category defined in a dictionary.

Key concepts relevant to this codebase:

- **Dictionary terms** can include a trailing wildcard (`*`). During counting, `abandon*` is expanded against the actual corpus vocabulary to match tokens like *abandoned*, *abandoning*, etc. Expansion is per-corpus — only tokens present in the text are matched.
- **Multi-category membership**: a single term can belong to multiple categories (e.g., "coach" in Basketball, Baseball, and Football). Categories can also be hierarchical in LIWC's built-in dictionaries (e.g., anger → negative emotion → emotion), though liwca treats them as flat columns.
- **File formats**: `.dic` (tab-delimited with `%` header delimiters) and `.dicx` (CSV with `X`/empty values). See the `io.py` module docstring for full format specs.

## Code Style

- Ruff: line length 100, target Python 3.14, rules `E, F, I, W, C90, NPY201`
- Docstrings: NumPy convention
- Formatting: double quotes, LF line endings
