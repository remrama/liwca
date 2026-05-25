> [!CAUTION]
> This package is a work in progress and under active development. Features have not been tested and may change without notice.

[![PyPI](https://img.shields.io/pypi/v/liwca.svg)](https://pypi.org/project/liwca)
[![Python Versions](https://img.shields.io/pypi/pyversions/liwca.svg)](https://pypi.org/project/liwca)
[![Downloads](https://static.pepy.tech/badge/liwca)](https://pepy.tech/projects/liwca)
[![License](https://img.shields.io/pypi/l/liwca.svg)](https://github.com/remrama/liwca/blob/main/LICENSE.txt)
[![Tests](https://github.com/remrama/liwca/actions/workflows/tests.yaml/badge.svg)](https://github.com/remrama/liwca/actions/workflows/tests.yaml)
[![Coverage](https://codecov.io/gh/remrama/liwca/branch/main/graph/badge.svg)](https://codecov.io/gh/remrama/liwca)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Repo Status](https://www.repostatus.org/badges/latest/wip.svg)](https://www.repostatus.org/#wip)

<p align="center">
    <picture>
        <source media="(prefers-color-scheme: dark)" srcset="docs/_static/banner-dark.png">
        <source media="(prefers-color-scheme: light)" srcset="docs/_static/banner.png">
        <img alt="liwca logo banner" src="docs/_static/banner.png">
    </picture>
</p>

**_liwca_** (*LOO-kə*), or **L**inguistic **I**nquiry **W**ord **C**ount **A**ssistant, provides helpers for working with [LIWC](https://www.liwc.app) dictionaries and related text analyses in Python.

- Read, write, and merge dictionary files (`.dic`, `dicx`)
- Generate category and word frequencies
- Generate Distributed Dictionary Representation ([DDR](https://link.springer.com/article/10.3758/s13428-017-0875-9)) scores
- Run the LIWC app from Python (requires `LIWC-22-cli` access)
- Download publicly accessible dictionaries, corpora, and other relevant datasets

See the [online docs](https://remrama.github.io/liwca) for more detail.

> [!NOTE]
> This is a personal project and not affiliated with the official LIWC app or any of the companies behind it.

## Installation

```shell
pip install --upgrade liwca
```

## Usage

### Input/output

Read and write local LIWC-style dictionary files as Pandas DataFrames with schema validation.

```python
import liwca

# Read a local dic file
dx = liwca.read_dic("my.dic")

# Read a local dicx file
dx = liwca.read_dicx("my.dicx")

# Read a local weighted dicx file
dx = liwca.read_dicx_weighted("myweighted.dicx")

# Create a dictionary from a collection of words
dx = liwca.create_dx(
    {
        "fruit": ["apple*", "pear*"],
        "vegetables": ["broccoli", "carrot*"],
    }
)

# Write the dictionary to a new file of any type
liwca.write_dic(dx, "fruit.dic")
liwca.write_dicx(dx, "fruit.dicx")
liwca.write_dicx_weighted(dx, "fruitweighted.dicx")
```

### Word counting

Get category-level frequency scores for each text in a corpus. This will provide similar results to `liwca.Liwc22().wc()`, but does not require the LIWC-22 app and has the optional benefit of returning word-level frequencies. This is possible because the [CountVectorizer](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.CountVectorizer.html) from `scikit-learn` is used to calculate frequencies instead of the LIWC-22 app.

> [!WARNING]
> Because the LIWC-22 app is not used to generate frequencies here, proprietary dictionaries built into the LIWC-22 app (e.g., `LIWC2015`, `LIWC22`) are not supported in `liwca.count()`.

```python
import liwca

# Generate some sample data
food_texts = [
    "My friends likes apples.",
    "She prefers pears over carrots.",
    "What I would do for a carrot right now!",
    "I am excited for pancakes tomorrow morning.",
]
food_categories = {
    "fruit": ["apple*", "pear*"],
    "vegetables": ["broccoli", "carrot*"],
}
food_dx = liwca.create_dx(food_categories)

# Return results at the category and word levels
cat_scores, word_scores = liwca.count(food_texts, food_dx, return_words=True)

cat_scores
# Category  WC  fruit  vegetables
# text_id
# 0          4   0.25    0.000000
# 1          5   0.20    0.200000
# 2          9   0.00    0.111111
# 3          7   0.00    0.000000

word_scores
#          WC  apples  broccoli    carrot  carrots  pears
# text_id
# 0         4    0.25       0.0       0.0      0.0    0.0
# 1         5     0.0       0.0       0.0      0.2    0.2
# 2         9     0.0       0.0  0.111111      0.0    0.0
# 3         7     0.0       0.0       0.0      0.0    0.0
```

### LIWC-22 CLI wrapper

The primary benefits of the LIWC-22 CLI wrapper are:

- Opens and closes the LIWC-22 app automatically and keeps it in the background (GUI does not open)
- Pure Python implementation (e.g., cleaner scripts if pre/post operations are also in Python)
- Cleaner argument names (e.g., text_columns instead of id_columns)
- Cleaner argument types (e.g., bool True/False instead of yes/no strings)
- Improved formatting for results output file (e.g., keep original row ID column name instead of renaming to id)

> [!CAUTION]
> This feature requires the LIWC-22 app installed locally from an academic license. See the [LIWC-22 CLI help page](https://www.liwc.app/help/cli) for more info.

```python
import liwca
import pandas as pd

texts = pd.Series(food_texts)
outpath = "./test_results.csv"

with liwca.Liwc22() as liwc:
    liwc.wc(texts, outpath, include_categories=["Tone", "ppron", "food", "death"])

cat_scores = pd.read_csv(outpath, index_col=0)
#          Tone  ppron   food  death
# Row ID
# 1       99.00  25.00   0.00      0
# 2       20.23  20.00   0.00      0
# 3       20.23  11.11   0.00      0
# 4       99.00  14.29  14.29      0

cat_scores.dtypes
# Tone     float64
# ppron    float64
# food     float64
# death      int64
# dtype: object
```

### Fetch public datasets

The `liwca.datasets` subpackage has multiple modules for fetching publicly available resources. Fetching includes downloading the file (if not already downloaded), caching it in local storage (to prevent re-downloading next time), preprocessing the file to fit standard formats, and also caching the preprocessed version.

```python
from liwca.datasets import corpora, dictionaries

texts = corpora.fetch_hippocorpus()
texts.columns
# Index(['AssignmentId', 'WorkTimeInSeconds', 'WorkerId', 'annotatorAge',
#        'annotatorGender', 'annotatorRace', 'distracted', 'draining',
#        'frequency', 'importance', 'logTimeSinceEvent', 'mainEvent', 'memType',
#        'mostSurprising', 'openness', 'recAgnPairId', 'recImgPairId',
#        'similarity', 'similarityReason', 'story', 'stressful', 'summary',
#        'timeSinceEvent'],
#       dtype='str')

texts["story"].head()
# 0    Concerts are my most favorite thing, and my bo...
# 1    The day started perfectly, with a great drive ...
# 2    It seems just like yesterday but today makes f...
# 3    Five months ago, my niece and nephew were born...
# 4    About a month ago I went to burning man. I was...
# Name: story, dtype: str

dx = dictionaries.fetch_threat()
# Category     threat
# DicTerm
# accidents         1
# accusations       1
# advised           1
# afraid            1
# aftermath         1
# ...             ...
# woes              1
# worries           1
# worry             1
# worse             1
# worst             1
```

## Similar projects

- [liwc-python](https://github.com/chbrown/liwc-python)
- [lingmatch](https://github.com/miserman/lingmatch)
- [pyliwc](https://github.com/camille1/pyliwc)
- [qdap](https://github.com/trinker/qdap) / [qdapDictionaries](https://github.com/trinker/qdapDictionaries)
- [sentibank](https://github.com/socius-org/sentibank)
- [sentidict](https://github.com/andyreagan/sentidict)
- [Shifterator](https://github.com/ryanjgallagher/shifterator)
