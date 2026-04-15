[![PyPI](https://img.shields.io/pypi/v/liwca.svg)](https://pypi.org/project/liwca)
[![Python Versions](https://img.shields.io/pypi/pyversions/liwca.svg)](https://pypi.org/project/liwca)
[![Downloads](https://static.pepy.tech/badge/liwca)](https://pepy.tech/projects/liwca)
[![License](https://img.shields.io/pypi/l/liwca.svg)](https://github.com/remrama/liwca/blob/main/LICENSE.txt)
[![Tests](https://github.com/remrama/liwca/actions/workflows/tests.yaml/badge.svg)](https://github.com/remrama/liwca/actions/workflows/tests.yaml)
[![Coverage](https://codecov.io/gh/remrama/liwca/branch/main/graph/badge.svg)](https://codecov.io/gh/remrama/liwca)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Repo Status](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)

# LIWCA

LIWCA (Linguistic Inquiry Word Count Assistant) offers helper functions for working with LIWC dictionaries. Useful when you want end-to-end pipelines or notebook workflows that don't require the LIWC-22 app to be open, or when you just need reusable `.dic[x]` file I/O without writing it from scratch every project.

Features:

- Reading and writing dictionary files (`.dic`/`.dicx`)
- Merging dictionary files
- Fetching public LIWC-format dictionaries from remote repositories
- Pure-Python word counting (no LIWC-22 needed)
- Calling `liwc-22-cli` from Python

## Installation

```shell
pip install --upgrade liwca
```

## Quick Start

```python
import liwca

# Fetch a public dictionary and count words (no LIWC-22 needed)
dx = liwca.fetch_threat()
results = liwca.count(["danger lurks ahead"], dx)
```

## Usage

### Fetching dictionaries

```python
import liwca

dx = liwca.fetch_sleep()           # Fetch and load a public dictionary
dx = liwca.fetch_bigtwo()          # Versioned dictionary (version="a" by default)
dx = liwca.read_dx("./my.dicx")    # Read a local dictionary file
liwca.write_dx(dx, "./my.dic")     # Write to a different format
```

### Word counting

Pure-Python word counting using LIWC-style dictionaries (no LIWC-22 needed).

```python
texts = ["I feel happy today", "This is a sad story"]
results = liwca.count(texts, dx)                      # percentages (default)
results = liwca.count(texts, dx, as_percentage=False)  # raw counts
```

### LIWC-22 wrapper (requires LIWC-22)

The LIWC-22 desktop application (or its license server) must be running when you call the CLI.
See the [LIWC CLI documentation](https://www.liwc.app/help/cli) and [Python CLI example](https://github.com/ryanboyd/liwc-22-cli-python/blob/main/LIWC-22-cli_Example.py) for more details.

```python
liwca.liwc22.wc(input="data.csv", output="results.csv")
```

## Similar Projects

- [liwc-python](https://github.com/chbrown/liwc-python)
- [lingmatch](https://github.com/miserman/lingmatch)
- [sentibank](https://github.com/socius-org/sentibank)