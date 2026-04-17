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

Five modules under `src/liwca/`:

- **`io.py`** - Read/write `.dic` and `.dicx` dictionary files, create and merge dictionaries. All dictionary DataFrames are validated through a Pandera schema (`dx_schema`) that enforces: lowercase string index named "DicTerm", binary int8 values, sorted columns named "Category".

- **`count.py`** - Pure-Python LIWC-style word counting (no LIWC-22 needed). Uses scikit-learn's `CountVectorizer`. Dictionary wildcards (e.g., `abandon*`) are expanded against the actual corpus vocabulary before counting.

- **`ddr.py`** - Distributed Dictionary Representation (DDR) scoring. Computes cosine similarity between document vectors and dictionary category centroids in word-embedding space. Accepts embeddings as a gensim model name (string) or any dict-like mapping. Optional dependency: `gensim>=4.0` via `pip install liwca[ddr]`.

- **`fetchers.py`** - Per-dictionary `fetch_*()` functions that download remote LIWC-format dictionaries via Pooch and return validated DataFrames. The Pooch registry (`data/registry.txt`) is the single source of truth for filenames, MD5 hashes, and download URLs. Includes custom parsers for non-standard formats (Excel, TSV, plain text).

- **`liwc22.py`** - Python wrapper around `liwc-22-cli`. Exposes a `Liwc22` class whose constructor hoists the cross-cutting CLI args (args that apply to ≥5 of the 7 modes: `encoding`, `count_urls`, `preprocess_cjk`, `include_subfolders`, `url_regexp`, `csv_delimiter`, `csv_escape`, `csv_quote`, `skip_header`, `precision`) plus execution-control flags (`auto_open`, `use_gui`, `dry_run`). The seven per-mode methods (`wc`, `freq`, `mem`, `context`, `arc`, `ct`, `lsm`) take only mode-specific kwargs. Each method accepts `input` as either a filepath (`str`) or a `pandas.DataFrame` (written to a temp CSV and cleaned up afterwards) and returns the `output` path on success (`None` when `dry_run=True`); CLI errors propagate as `subprocess.CalledProcessError`. The `wc` output file is reshaped in place via `wc_output_schema` (Row ID renamed, constant Segment dropped, column axis named `Category`). Can be used as a context manager to amortize LIWC-22 app launch/shutdown. Internally: `FLAG_BY_DEST` maps each Python dest to its CLI flag; flag-category frozensets dispatch translation in `build_command` — `BOOL_FLAGS` (value-less), `YES_NO_FLAGS` (`bool` → `"yes"`/`"no"`), `ONE_ZERO_FLAGS` (`bool` → `"1"`/`"0"`), `LIST_FLAGS` (`Iterable[str]` → comma-joined), plus `COLUMN_FLAGS` and `COLUMN_LIST_FLAGS` (0-based `int` or column-name `str` → 1-based int, resolved upstream by `_resolve_columns`). `MODE_GLOBALS` filters which hoisted args apply to each mode (e.g. `count_urls` is dropped for `lsm`).

## LIWC Domain Context

LIWC (Linguistic Inquiry and Word Count) is a dictionary-based text analysis method. Texts are scored by counting how many words fall into each psychological/linguistic category defined in a dictionary.

Key concepts relevant to this codebase:

- **Dictionary terms** can include a trailing wildcard (`*`). During counting, `abandon*` is expanded against the actual corpus vocabulary to match tokens like *abandoned*, *abandoning*, etc. Expansion is per-corpus - only tokens present in the text are matched.
- **Multi-category membership**: a single term can belong to multiple categories (e.g., "coach" in Basketball, Baseball, and Football). Categories can also be hierarchical in LIWC's built-in dictionaries (e.g., anger → negative emotion → emotion), though liwca treats them as flat columns.
- **File formats**: `.dic` (tab-delimited with `%` header delimiters) and `.dicx` (CSV with `X`/empty values). See the `io.py` module docstring for full format specs.

## Code Style

- Ruff: line length 100, target Python 3.14, rules `E, F, I, W, C90, NPY201`
- Docstrings: NumPy convention
- Formatting: double quotes, LF line endings
