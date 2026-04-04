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

## Usage

### IO

```python
import liwca

# Download and read a public dictionary files
dx = liwca.fetch_dx("sleep")

# Read local dictionary files
dx = liwca.read_dx("./sleep.dic")
dx = liwca.read_dx("./sleep.dicx")

# Write local dictionary files
liwca.write_dx(dx, "./sleep.dic")
liwca.write_dx(dx, "./sleep.dicx")
```

### Counting

Pure-Python word counting using LIWC-style dictionaries (no LIWC-22 installation required).

```python
import liwca

dx = liwca.read_dx("my_dictionary.dicx")

texts = ["I feel happy today", "This is a sad story"]
results = liwca.count(texts, dx)  # returns DataFrame with category percentages

# Get raw counts instead of proportions
results = liwca.count(texts, dx, as_proportion=False)
```

### CLI

Wraps `liwc-22-cli` for analysis from the command line (requires LIWC-22).

```bash
# Word count analysis
liwca wc -i data.csv -o results.csv

# Frequency analysis
liwca freq -i corpus/ -o frequencies.csv

# Auto-launch LIWC-22 if not already running
liwca wc -i data.csv -o results.csv --auto-open

# Preview the command without executing
liwca wc -i data.csv -o results.csv --dry-run

# View all possible arguments for the word count analysis
liwca wc --help
```

## Similar Projects

- [liwc-python](https://github.com/chbrown/liwc-python)
- [lingmatch](https://github.com/miserman/lingmatch)
- [sentibank](https://github.com/socius-org/sentibank)