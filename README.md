[![PyPI](https://img.shields.io/pypi/v/liwca.svg)](https://pypi.org/project/liwca)
[![Python Versions](https://img.shields.io/pypi/pyversions/liwca.svg)](https://pypi.org/project/liwca)
[![Downloads](https://static.pepy.tech/badge/liwca)](https://pepy.tech/projects/liwca)
[![License](https://img.shields.io/pypi/l/liwca.svg)](https://github.com/remrama/liwca/blob/main/LICENSE.txt)
[![Tests](https://github.com/remrama/liwca/actions/workflows/tests.yaml/badge.svg)](https://github.com/remrama/liwca/actions/workflows/tests.yaml)
[![Coverage](https://codecov.io/gh/remrama/liwca/branch/main/graph/badge.svg)](https://codecov.io/gh/remrama/liwca)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Repo Status](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)

<p align="center">
    <picture>
        <source media="(prefers-color-scheme: dark)" srcset="docs/_static/banner-dark.png">
        <source media="(prefers-color-scheme: light)" srcset="docs/_static/banner.png">
        <img alt="liwca logo banner" src="docs/_static/banner.png">
    </picture>
</p>

**_liwca_** (Linguistic Inquiry Word Count Assistant) offers helper functions for working with LIWC dictionaries. Useful when you want end-to-end pipelines or notebook workflows that don't require the LIWC-22 app to be open, or when you just need reusable `.dic[x]` file I/O without writing it from scratch every project. See the [online docs](https://remrama.github.io/liwca).

Features:

- Calling `LIWC-22-cli` from Python
- Pure-Python word counting (no LIWC-22 needed)
- Distributed Dictionary Representation scoring
- Reading, writing, and merging dictionary files (`.dic`/`.dicx`)
- Downloading public datasets, including dictionaries, corpora, and relevant tables

## Installation

```shell
pip install --upgrade liwca
```

## Usage

### LIWC-22 wrapper

Requires LIWC-22 app with academic license installed locally.

```python
import liwca

with liwca.Liwc22(count_urls=True) as liwc:
    outpath = liwc.wc(
        "data.csv",
        "liwc-results.csv",
        dictionary="LIWC22",
        text_columns="text",
    )
```

### Word counting

Pure-Python word counting using LIWC-style dictionaries (no LIWC-22 installation required).

```python
import liwca
from liwca.datasets import dictionaries
texts = ["I feel happy today", "This is a sad story"]
dx = dictionaries.fetch_emfd()

# Return results at document level
doc_scores = liwca.count(texts, dx)

# Return results at document and word level
doc_scores, word_scores = liwca.count(texts, dx, return_words=True)
```

### Input/output

Read and write LIWC-style dictionary files with schema validation.

```python
import liwca

# Read a dic file
dx = liwca.read_dic("my.dic")

# Read a dicx file
dx = liwca.read_dicx("my.dicx")

# Read a weighted dicx file
dx = liwca.read_dicx_weighted("myweighted.dicx")

# Write to any similar file type
dx.write_dic("mynew.dic")
dx.write_dicx("mynew.dicx")
dx.write_dicx_weighted("mynewweighted.dicx")
```

### Downloading datasets

Fetch public datasets, including dictionaries and corpora.

```python
from liwca.datasets import corpora, dictionaries

data = corpora.fetch_cmu_book_summaries()
dx = dictionaries.fetch_threat()
results = liwca.count(data, dx)
```

## Similar projects

- [liwc-python](https://github.com/chbrown/liwc-python)
- [lingmatch](https://github.com/miserman/lingmatch)
- [pyliwc](https://github.com/camille1/pyliwc)
- [qdap](https://github.com/trinker/qdap) / [qdapDictionaries](https://github.com/trinker/qdapDictionaries)
- [sentibank](https://github.com/socius-org/sentibank)
- [sentidict](https://github.com/andyreagan/sentidict)
- [Shifterator](https://github.com/ryanjgallagher/shifterator)

### Dataset resources

- [Noah's ARK](https://noahs-ark.github.io) ([archived Noah's ARK](https://www.cs.cmu.edu/~ark))
- [Psycho/Neurolinguistic Databases & Resources](https://www.reilly-coglab.com/data)
- [LitBank](https://github.com/dbamman/litbank)
- [DreamBank](https://github.com/mattbierner/DreamScrape)
- [Shifterator lexicons](https://github.com/ryanjgallagher/shifterator/tree/master/shifterator/lexicons)
- [Standup comedy transcripts and LIWC results table](https://link.springer.com/article/10.1186/s40359-024-02187-6)