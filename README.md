[![Project Status](https://www.repostatus.org/badges/latest/wip.svg)](https://www.repostatus.org/#wip)
[![PyPI](https://img.shields.io/pypi/v/liwca.svg)](https://pypi.python.org/pypi/liwca)
[![Python Versions](https://img.shields.io/pypi/pyversions/liwca.svg)](https://pypi.python.org/pypi/ruff)
[![License](https://img.shields.io/pypi/l/liwca.svg)](https://github.com/remrama/liwca/blob/main/LICENSE.txt)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

# LIWCA

LIWCA is a Linguistic Inquiry Word Count Assistant. It is not a copy of [LIWC](https://liwc.app) (they don't like that), it is just helper functions that I've found useful.

Stuff like:

- Reading and writing dictionary files (`.dic[x]`)
- Converting between `.dic` and `.dicx` files
- Converting between dictionary (`.dic[x]`) and tabular (`.[c|t]sv`) files
- Merging dictionary files
- Fetching public dictionary files from remote repositories
- Calling `liwc-22-cli` from Python (opens/closes the LIWC-22 app in background as needed)

## Installation

```shell
pip install --upgrade liwca
```

## Quick Start

```bash
# LIWC-22 CLI wrapper (requires LIWC-22)
liwca wc -i data.csv -o results.csv
```

```python
import liwca

# Fetch a public dictionary and count words (no LIWC-22 needed)
dx = liwca.fetch_dx("threat")
results = liwca.count(["danger lurks ahead"], dx)
```

## Usage

### CLI (requires LIWC-22)

```bash
liwca wc -i data.csv -o results.csv          # Word count analysis
liwca freq -i corpus/ -o frequencies.csv      # Frequency analysis
liwca wc -i data.csv -o results.csv --auto-open  # Auto-launch LIWC-22
liwca wc --help                               # View all arguments
```

### Dictionary I/O

```python
import liwca

liwca.list_available()              # See available remote dictionaries
dx = liwca.fetch_dx("sleep")       # Fetch and load a public dictionary
dx = liwca.read_dx("./my.dicx")    # Read a local dictionary file
liwca.write_dx(dx, "./my.dic")     # Write to a different format
```

### Word Counting

Pure-Python word counting using LIWC-style dictionaries (no LIWC-22 needed).

```python
texts = ["I feel happy today", "This is a sad story"]
results = liwca.count(texts, dx)                      # percentages (default)
results = liwca.count(texts, dx, as_percentage=False)  # raw counts
```

## Similar Projects

- [liwc-python](https://github.com/chbrown/liwc-python)
- [lingmatch](https://github.com/miserman/lingmatch)
- [sentibank](https://github.com/socius-org/sentibank)