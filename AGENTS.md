# AGENTS.md

This file provides guidance to AI coding agents (Claude Code, GitHub Copilot, etc.) when working with code in this repository.

## Project Overview

LIWCA is a Python helper library for working with [LIWC](https://liwc.app) dictionaries. It provides pure-Python word counting, dictionary file I/O (`.dic`/`.dicx`), remote dictionary/corpus/table fetching, distributed dictionary representations (DDR), and a CLI wrapper around `liwc-22-cli`.

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

Always use `uv` when running Python scripts or installing dependencies. Never use bare `pip install` or `python`.

## Architecture

### Core modules (`src/liwca/`)

- **`io.py`** — Read/write `.dic` and `.dicx` dictionary files, create and merge dictionaries. All dictionary DataFrames are validated through a Pandera schema (`dx_schema`) that enforces: lowercase string index named `"DicTerm"`, binary int8 values, sorted columns named `"Category"`.

- **`count.py`** — Pure-Python LIWC-style word counting (no LIWC-22 needed). Uses scikit-learn's `CountVectorizer`. Dictionary wildcards (e.g., `abandon*`) are expanded against the actual corpus vocabulary before counting.

- **`ddr.py`** — Distributed Dictionary Representation (DDR) scoring. Computes cosine similarity between document vectors and dictionary category centroids in word-embedding space. Accepts embeddings as a gensim model name (string) or any dict-like mapping. Optional dependency: `gensim>=4.0` via `pip install liwca[ddr]`.

- **`liwc22.py`** — Python wrapper around `liwc-22-cli`. Exposes a `Liwc22` class whose constructor hoists the cross-cutting CLI args (args that apply to ≥5 of the 7 modes: `encoding`, `count_urls`, `preprocess_cjk`, `include_subfolders`, `url_regex`, `csv_delimiter`, `csv_escape`, `csv_quote`, `skip_header`, `precision`) plus execution-control flags (`auto_open`, `use_gui`, `dry_run`). The seven per-mode methods (`wc`, `freq`, `mem`, `context`, `arc`, `ct`, `lsm`) take only mode-specific kwargs. Each method accepts `input` as either a filepath (`str`) or a `pandas.DataFrame` (written to a temp CSV and cleaned up afterwards) and returns the `output` path on success (`None` when `dry_run=True`); CLI errors propagate as `subprocess.CalledProcessError`. The `wc` output file is reshaped in place via `wc_output_schema` (Row ID renamed, constant Segment dropped, column axis named `Category`). Can be used as a context manager to amortize LIWC-22 app launch/shutdown. Internally: `FLAG_BY_DEST` maps each Python dest to its CLI flag; flag-category frozensets dispatch translation in `build_command` — `BOOL_FLAGS` (value-less), `YES_NO_FLAGS` (`bool` → `"yes"`/`"no"`), `ONE_ZERO_FLAGS` (`bool` → `"1"`/`"0"`), `LIST_FLAGS` (`Iterable[str]` → comma-joined), plus `COLUMN_FLAGS` and `COLUMN_LIST_FLAGS` (0-based `int` or column-name `str` → 1-based int, resolved upstream by `_resolve_columns`). `MODE_GLOBALS` filters which hoisted args apply to each mode (e.g. `count_urls` is dropped for `lsm`).

### Datasets subpackage (`src/liwca/datasets/`)

All remote data is fetched via [Pooch](https://www.fatiando.org/pooch/) and cached locally. Cache root defaults to `pooch.os_cache("liwca")` and can be overridden with `$LIWCA_DATA_DIR`. The shared registry file at `src/liwca/datasets/data/registry.txt` is the single source of truth for filenames, MD5 hashes, and download URLs.

- **`_common.py`** — Shared helpers: `make_pup(category)` builds a `pooch.Pooch` for one cache subdirectory (`"dictionaries"`, `"corpora"`, or `"tables"`), all loading the same `registry.txt`. Also defines `UnzipToCsv` and `CacheCsv` processors (download-and-parse-once caching), and `AuthorizedZenodoDownloader` (lazily injects a `ZENODO_TOKEN` bearer header for restricted-access datasets).

- **`dictionaries.py`** — Per-dictionary `fetch_*()` functions that download remote LIWC-format dictionaries and return validated DataFrames. Includes custom parsers for non-standard formats. Public functions: `fetch_bigtwo`, `fetch_emfd`, `fetch_empath`, `fetch_hedonometer`, `fetch_honor`, `fetch_leeq`, `fetch_mystical`, `fetch_psychnorms`, `fetch_scope`, `fetch_sleep`, `fetch_threat`, `fetch_wrad`. Also exposes `path(name, **kwargs)` to get the local `.dicx` path for a named dictionary, and `list_psychnorms_stems` / `list_scope_stems` for multi-stem dictionaries.

- **`corpora.py`** — Per-corpus `fetch_*()` functions returning local `Path` objects to downloaded text corpora. Public functions: `fetch_autobiomemsim`, `fetch_cmu_book_summaries`, `fetch_cmu_movie_summaries`, `fetch_hippocorpus`, `fetch_liwc22_demo_data`, `fetch_reddit_short_stories`, `fetch_sherlock`, `fetch_tedtalks`.

- **`tables.py`** — Per-table `fetch_*()` functions returning local `Path` objects to downloaded norm/statistics tables. Public functions: `fetch_liwc2015norms`, `fetch_liwc22norms`, `fetch_psychnorms`, `fetch_scope`.

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
