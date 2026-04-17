"""
Distributed Dictionary Representation (DDR) scoring.

Scores documents against dictionary categories using cosine similarity in
word-embedding space, following the DDR method (Garten et al., 2018).  Unlike
exact word counting (:func:`liwca.count`), DDR captures semantic proximity
even when the exact dictionary words are absent from a document.

Algorithm
---------
1. For each dictionary category, compute a **centroid vector** - the mean of
   its terms' word embeddings.
2. For each document, compute a **document vector** - the mean of its tokens'
   word embeddings.
3. Score each (document, category) pair as the cosine similarity between the
   document vector and the category centroid.

Wildcard Handling
-----------------
Dictionary terms ending in ``*`` (e.g., ``abandon*``) have the wildcard
stripped and the bare stem is looked up in the embedding vocabulary.  If the
stem is not found, the term is silently skipped (logged at DEBUG level).

Out-of-Vocabulary (OOV) Behaviour
----------------------------------
- Tokens not in the embedding vocabulary are skipped when computing means.
- If **all** tokens in a document are OOV the document vector is undefined
  and all category scores are ``NaN``.
- If **all** terms in a category are OOV the category centroid is undefined
  and that column is ``NaN`` for every document.
"""

from __future__ import annotations

import functools
import logging
import re
from collections.abc import Callable, Iterable, Mapping
from typing import Union, cast

import numpy as np
import pandas as pd
from numpy.typing import ArrayLike
from sklearn.metrics.pairwise import cosine_similarity

__all__ = [
    "ddr",
]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default tokenizer (duplicated from count.py to keep modules self-contained)
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[a-zA-Z\u00C0-\u024F][''\w]*", re.UNICODE)


def _default_tokenize(text: str) -> list[str]:
    """Lowercase regex tokenizer that preserves contractions."""
    return [m.group().lower() for m in _TOKEN_RE.finditer(text)]


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=4)
def _load_gensim_model(name: str) -> Mapping[str, ArrayLike]:
    """Load a gensim model by name, caching the result across calls."""
    try:
        import gensim.downloader as gensim_api
    except ImportError:
        raise ImportError(
            f"gensim is required to load embeddings by name ('{name}'). "
            "Install it with:  pip install liwca[ddr]"
        ) from None
    logger.info("Loading gensim model '%s'", name)
    return cast(Mapping[str, ArrayLike], gensim_api.load(name))


def _load_embeddings(embeddings: str | Mapping[str, ArrayLike]) -> Mapping[str, ArrayLike]:
    """Return a mapping from words to vectors.

    If *embeddings* is a string it is treated as a gensim model name and
    loaded via :func:`gensim.downloader.load` (cached so repeated calls
    with the same name are instant).  Otherwise it is returned as-is.
    """
    if isinstance(embeddings, str):
        return _load_gensim_model(embeddings)
    return embeddings


def _infer_dim(
    embeddings: Mapping[str, ArrayLike],
    dx: pd.DataFrame,
    tokenizer: Callable[[str], list[str]],
    docs: list[str],
) -> int:
    """Determine the embedding dimensionality from the first available vector."""
    for term in dx.index:
        clean = str(term).rstrip("*")
        if clean in embeddings:
            return len(embeddings[clean])  # type: ignore[arg-type]
    for doc in docs:
        for tok in tokenizer(doc):
            if tok in embeddings:
                return len(embeddings[tok])  # type: ignore[arg-type]
    raise ValueError(
        "Cannot determine embedding dimensionality: no dictionary terms "
        "or document tokens found in the embeddings vocabulary."
    )


def _build_centroids(
    dx: pd.DataFrame,
    categories: list[str],
    embeddings: Mapping[str, ArrayLike],
) -> dict[str, np.ndarray | None]:
    """Compute the mean embedding vector for each dictionary category.

    Returns a dict mapping category name to its centroid vector, or ``None``
    when every term in the category is out-of-vocabulary.
    """
    centroids: dict[str, np.ndarray | None] = {}
    for cat in categories:
        terms = dx.index[dx[cat] == 1]
        vectors: list[np.ndarray] = []
        for term in terms:
            clean = str(term).rstrip("*")
            if clean in embeddings:
                vectors.append(np.asarray(embeddings[clean], dtype=np.float64))
            else:
                logger.debug("Category '%s': term '%s' not in embeddings", cat, clean)
        if vectors:
            centroids[cat] = np.mean(vectors, axis=0)
        else:
            centroids[cat] = None
            logger.warning("Category '%s': no terms found in embeddings", cat)
    return centroids


def _build_doc_vectors(
    docs: list[str],
    tokenizer: Callable[[str], list[str]],
    embeddings: Mapping[str, ArrayLike],
    dim: int,
) -> np.ndarray:
    """Compute the mean embedding vector for each document.

    Returns an ``(n_docs, dim)`` array.  Rows where every token is
    out-of-vocabulary are filled with ``NaN``.
    """
    doc_vectors = np.full((len(docs), dim), np.nan, dtype=np.float64)
    for i, doc in enumerate(docs):
        tokens = tokenizer(doc)
        vectors: list[np.ndarray] = []
        for tok in tokens:
            if tok in embeddings:
                vectors.append(np.asarray(embeddings[tok], dtype=np.float64))
        if vectors:
            doc_vectors[i] = np.mean(vectors, axis=0)
    return doc_vectors


def _compute_similarities(
    doc_vectors: np.ndarray,
    centroids: dict[str, np.ndarray | None],
    categories: list[str],
) -> dict[str, np.ndarray]:
    """Cosine similarity between each document vector and each category centroid.

    Returns a dict of ``{category: scores}`` arrays.  Documents or categories
    with undefined vectors produce ``NaN``.
    """
    n_docs = doc_vectors.shape[0]
    valid = ~np.isnan(doc_vectors[:, 0])
    result_data: dict[str, np.ndarray] = {}
    for cat in categories:
        centroid = centroids[cat]
        if centroid is None:
            result_data[cat] = np.full(n_docs, np.nan)
        else:
            scores = np.full(n_docs, np.nan)
            if valid.any():
                scores[valid] = cosine_similarity(
                    doc_vectors[valid], centroid.reshape(1, -1)
                ).ravel()
            result_data[cat] = scores
    return result_data


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def ddr(
    texts: Union[Iterable[str], pd.Series],
    dx: pd.DataFrame,
    embeddings: Union[str, Mapping[str, ArrayLike]],
    *,
    tokenizer: Callable[[str], list[str]] | None = None,
    precision: int | None = None,
) -> pd.DataFrame:
    """
    Score documents against dictionary categories via DDR.

    Parameters
    ----------
    texts : :class:`~collections.abc.Iterable` of :class:`str` or :class:`~pandas.Series`
        The documents to score.  Each element is a single document string.
    dx : :class:`~pandas.DataFrame`
        A LIWC dictionary DataFrame as returned by :func:`liwca.read_dx`.
        Index contains dictionary terms (may include ``*`` wildcards),
        columns are category names, values are binary (0/1).
    embeddings : :class:`str` or :class:`~collections.abc.Mapping`
        Word embeddings to use.  Pass a **string** to load a pre-trained
        model via :func:`gensim.downloader.load` (requires
        ``pip install liwca[ddr]``), e.g. ``"glove-wiki-gigaword-100"``.
        Or pass any mapping that supports ``embeddings[word]`` and
        ``word in embeddings`` - a plain :class:`dict`, gensim
        :class:`~gensim.models.keyedvectors.KeyedVectors`, etc.
    tokenizer : :class:`~collections.abc.Callable`, optional
        A function ``str -> list[str]`` used to split each document into
        lowercase tokens.  Defaults to a regex tokenizer that preserves
        contractions (identical to :func:`liwca.count`'s default).
    precision : :class:`int`, optional
        If set, round cosine similarity values to this many decimal places.

    Returns
    -------
    :class:`~pandas.DataFrame`
        A *documents x categories* DataFrame.  Index matches the input
        order (or the :class:`~pandas.Series` index if a Series was passed).
        Columns are the sorted dictionary category names.  Values are cosine
        similarities in [-1, 1], or ``NaN`` when the document or category
        vector is undefined (see module docstring for OOV details).

    Examples
    --------
    >>> import liwca
    >>> dx = liwca.fetch_threat()  # doctest: +SKIP
    >>> results = liwca.ddr(
    ...     ["danger lurks ahead"],
    ...     dx,
    ...     "glove-wiki-gigaword-100",
    ... )  # doctest: +SKIP
    """
    embeddings = _load_embeddings(embeddings)

    if tokenizer is None:
        tokenizer = _default_tokenize

    # -- Materialise texts + build index (same pattern as count()) -------------
    if isinstance(texts, pd.Series):
        doc_index = texts.index
        if doc_index.name is None:
            doc_index = doc_index.copy()
            doc_index.name = "text_id"
        docs = texts.tolist()
    else:
        docs = list(texts)
        doc_index = pd.RangeIndex(len(docs), name="text_id")

    logger.info("DDR scoring %d documents against %d-category dictionary", len(docs), dx.shape[1])

    categories = list(dx.columns)  # already sorted by dx_schema
    dim = _infer_dim(embeddings, dx, tokenizer, docs)

    centroids = _build_centroids(dx, categories, embeddings)
    doc_vectors = _build_doc_vectors(docs, tokenizer, embeddings, dim)
    result_data = _compute_similarities(doc_vectors, centroids, categories)

    result = pd.DataFrame(result_data, index=doc_index)

    if precision is not None:
        result = result.round(precision)

    logger.debug("DDR scoring complete: %d documents, %d categories", len(docs), len(categories))
    return result
