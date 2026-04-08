"""
LIWC-style word counting (pure-Python, no LIWC-22 required).

Wildcard Handling
-----------------
LIWC dictionaries use trailing wildcards (e.g., ``abandon*``) to match any
token that starts with a given prefix.
Because :class:`~sklearn.feature_extraction.text.CountVectorizer` requires a flat vocabulary,
wildcards are **expanded against the actual corpus vocabulary** before vectorisation:

1. Tokenise all documents to collect unique corpus tokens.
2. For each wildcard entry, find every corpus token that starts with the prefix.
3. Map each matching token back to the wildcard's category memberships.
4. Merge with exact-match entries into a single expanded vocabulary.
5. Build a ``CountVectorizer`` with that vocabulary and transform the corpus.

This means results are deterministic for a given corpus + dictionary pair, but
the expanded vocabulary will differ across corpora (a token can only be counted
if it actually appears).
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Iterable
from typing import Literal, Union, overload

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer

__all__ = [
    "scikit",
]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default tokenizer
# ---------------------------------------------------------------------------

# Matches sequences of word characters + apostrophes (to keep contractions
# like "don't" as single tokens), then lowercases.  This is intentionally
# simple — users who need spaCy / NLTK tokenisation can pass their own
# callable via the *tokenizer* parameter.
_TOKEN_RE = re.compile(r"[a-zA-Z\u00C0-\u024F][''\w]*", re.UNICODE)


def _default_tokenize(text: str) -> list[str]:
    """Lowercase regex tokenizer that preserves contractions."""
    return [m.group().lower() for m in _TOKEN_RE.finditer(text)]


# ---------------------------------------------------------------------------
# Wildcard expansion
# ---------------------------------------------------------------------------


def _expand_wildcards(
    dx: pd.DataFrame,
    corpus_vocab: set[str],
) -> pd.DataFrame:
    """Expand wildcard dictionary entries against the corpus vocabulary.

    Parameters
    ----------
    dx : :class:`~pandas.DataFrame`
        Dictionary DataFrame (index = DicTerm, may contain ``*`` suffixes).
    corpus_vocab : :class:`set` of :class:`str`
        Set of unique lowercased tokens observed in the corpus.

    Returns
    -------
    :class:`~pandas.DataFrame`
        A new dictionary DataFrame with wildcards replaced by their matching
        corpus tokens.  Exact-match entries are preserved as-is (even if they
        don't appear in the corpus — :class:`~sklearn.feature_extraction.text.CountVectorizer`
        will simply ignore them).  If a corpus token matches both an exact entry
        and a wildcard, category memberships are merged (logical OR).
    """
    wildcard_mask = dx.index.str.endswith("*")
    exact = dx.loc[~wildcard_mask]
    wildcards = dx.loc[wildcard_mask]

    logger.debug("Dictionary has %d exact and %d wildcard entries", len(exact), len(wildcards))

    if wildcards.empty:
        return exact

    # Build expansion rows: for each wildcard prefix, find matching tokens.
    expanded_rows: dict[str, np.ndarray] = {}
    for term, row in wildcards.iterrows():
        prefix = str(term)[:-1]  # strip trailing *
        for token in corpus_vocab:
            if token.startswith(prefix):
                if token in expanded_rows:
                    # Merge (OR) with any prior mapping for this token.
                    expanded_rows[token] = np.maximum(expanded_rows[token], row.values)
                else:
                    expanded_rows[token] = row.values.copy()

    if not expanded_rows:
        logger.debug("No wildcard matches found in corpus vocabulary")
        return exact

    expanded_df = pd.DataFrame.from_dict(expanded_rows, orient="index", columns=exact.columns)
    expanded_df.index.name = "DicTerm"

    # Merge with exact entries (exact takes precedence via OR).
    combined = pd.concat([exact, expanded_df], axis=0)
    # If a token appears in both exact and expanded, merge rows.
    combined = combined.groupby(level=0).max()
    logger.debug(
        "Wildcard expansion: %d wildcards -> %d new tokens (%d total vocabulary)",
        len(wildcards),
        len(expanded_rows),
        len(combined),
    )
    return combined


# ---------------------------------------------------------------------------
# Word-level output helper
# ---------------------------------------------------------------------------


def _build_word_result(
    dtm: object | None,
    doc_index: pd.Index,
    vocab_tokens: list[str],
    word_counts: np.ndarray,
    as_percentage: bool,
    precision: int | None,
) -> pd.DataFrame:
    """Assemble a documents x tokens DataFrame from the raw DTM."""
    if dtm is None:
        word_result = pd.DataFrame(index=doc_index)
    else:
        word_result = pd.DataFrame.sparse.from_spmatrix(dtm, index=doc_index, columns=vocab_tokens)
        if as_percentage:
            safe_wc = np.where(word_counts > 0, word_counts, 1)
            word_result = word_result.div(safe_wc, axis=0) * 100
        if as_percentage and precision is not None:
            # Sparse arrays don't support .round(); densify first.
            word_result = word_result.sparse.to_dense().round(precision)

    word_result.insert(0, "WC", word_counts)
    return word_result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@overload
def scikit(
    texts: Union[Iterable[str], pd.Series],
    dx: pd.DataFrame,
    *,
    tokenizer: Callable[[str], list[str]] | None = ...,
    as_percentage: bool = ...,
    precision: int | None = ...,
    return_words: Literal[False] = ...,
) -> pd.DataFrame: ...


@overload
def scikit(
    texts: Union[Iterable[str], pd.Series],
    dx: pd.DataFrame,
    *,
    tokenizer: Callable[[str], list[str]] | None = ...,
    as_percentage: bool = ...,
    precision: int | None = ...,
    return_words: Literal[True],
) -> tuple[pd.DataFrame, pd.DataFrame]: ...


def scikit(
    texts: Union[Iterable[str], pd.Series],
    dx: pd.DataFrame,
    *,
    tokenizer: Callable[[str], list[str]] | None = None,
    as_percentage: bool = True,
    precision: int | None = None,
    return_words: bool = False,
) -> pd.DataFrame | tuple[pd.DataFrame, pd.DataFrame]:
    """
    Count LIWC dictionary categories across documents (pure-Python).

    Parameters
    ----------
    texts : :class:`~collections.abc.Iterable` of :class:`str` or :class:`~pandas.Series`
        The documents to analyse.  Each element is a single document string.
    dx : :class:`~pandas.DataFrame`
        A LIWC dictionary DataFrame as returned by :func:`liwca.read_dx`.
        Index contains dictionary terms (may include ``*`` wildcards),
        columns are category names, values are binary (0/1).
    tokenizer : :class:`~collections.abc.Callable`, optional
        A function ``str -> list[str]`` used to split each document into
        lowercase tokens.  Defaults to a regex tokenizer that preserves
        contractions (``don't`` → ``["don't"]``).
    as_percentage : :class:`bool`, optional
        If ``True`` (default), return category values as a percentage of total
        word count per document (matching LIWC's default output).  If
        ``False``, return raw category counts.
    precision : :class:`int`, optional
        If set, round category value columns to this many decimal places.
        Only applies when ``as_percentage=True``. The ``"WC"`` column is
        never rounded.
    return_words : :class:`bool`, optional
        If ``True``, return a tuple ``(categories, words)`` where *words* is
        a *documents × tokens* DataFrame holding per-word counts (or
        percentages) for every dictionary token that appeared in the corpus.
        Wildcard entries are expanded to the actual corpus tokens that
        matched (e.g., ``recall*`` → ``recalled``, ``recalling``, …).
        The same ``as_percentage`` and ``precision`` settings apply to both
        DataFrames.  Default ``False``.

    Returns
    -------
    :class:`~pandas.DataFrame` or tuple of :class:`~pandas.DataFrame`
        When ``return_words=False`` (default): a *documents × categories*
        DataFrame.  Index matches the input order (or the
        :class:`~pandas.Series` index if a Series was passed).  Columns are
        the dictionary category names.  An additional ``"WC"`` column
        contains the total word count for each document.

        When ``return_words=True``: a tuple ``(categories, words)`` where
        *categories* is the DataFrame described above and *words* is a
        *documents × tokens* DataFrame with one column per matched
        dictionary token plus a ``"WC"`` column.

    Examples
    --------
    >>> import liwca
    >>> dx = liwca.fetch_dx("threat")
    >>> texts = ["This is a grave threat to our safety.", "All is calm today."]
    >>> liwca.scikit(texts, dx)
    Category  WC  threat
    0          8    12.5
    1          4     0.0

    Get per-word contributions:

    >>> cats, words = liwca.scikit(texts, dx, return_words=True)
    >>> words.columns.tolist()
    ['WC', 'grave', 'threat']
    """
    if tokenizer is None:
        tokenizer = _default_tokenize

    # Materialise the texts so we can iterate twice (once for vocab, once for
    # vectorisation).  Preserve Series index if provided.
    if isinstance(texts, pd.Series):
        doc_index = texts.index
        if doc_index.name is None:
            doc_index = doc_index.copy()
            doc_index.name = "text_id"
        docs = texts.tolist()
    else:
        docs = list(texts)
        doc_index = pd.RangeIndex(len(docs), name="text_id")

    logger.info("Counting %d documents against %d-category dictionary", len(docs), dx.shape[1])

    # -- Step 1: collect corpus vocabulary -----------------------------------
    corpus_vocab: set[str] = set()
    for doc in docs:
        corpus_vocab.update(tokenizer(doc))
    logger.debug("Corpus vocabulary: %d unique tokens", len(corpus_vocab))

    # -- Step 2: expand wildcards --------------------------------------------
    dx_expanded = _expand_wildcards(dx, corpus_vocab)

    # Build the flat vocabulary mapping: token -> column index in the DTM.
    vocab_tokens = sorted(dx_expanded.index)
    vocab_map = {tok: i for i, tok in enumerate(vocab_tokens)}

    # -- Step 3: build document-term matrix via CountVectorizer --------------
    n_docs = len(docs)
    n_cats = dx_expanded.shape[1]

    if not vocab_map:
        # No dictionary terms matched any corpus tokens — all counts are zero.
        cat_counts = np.zeros((n_docs, n_cats), dtype=int)
        dtm = None
    else:
        vectorizer = CountVectorizer(
            analyzer=tokenizer,
            vocabulary=vocab_map,
            lowercase=False,  # tokenizer already lowercases
        )
        dtm = vectorizer.fit_transform(docs)  # (n_docs, n_vocab), sparse csr

        # -- Step 4: map token counts to category counts ---------------------
        # category_matrix: (n_vocab, n_categories), binary
        category_matrix = dx_expanded.loc[vocab_tokens].values  # aligned to vocab order

        # (n_docs, n_vocab) @ (n_vocab, n_categories) = (n_docs, n_categories)
        cat_counts = dtm @ category_matrix  # result is a dense ndarray

    # -- Step 5: compute word counts (total tokens per doc, not just matched)
    # We need a separate pass because the vocab-restricted DTM only counts
    # dictionary tokens.  If the corpus has zero unique tokens (all docs
    # empty), CountVectorizer would raise — short-circuit to zeros.
    if not corpus_vocab:
        word_counts = np.zeros(len(docs), dtype=int)
    else:
        wc_vectorizer = CountVectorizer(
            analyzer=tokenizer,
            lowercase=False,
        )
        wc_dtm = wc_vectorizer.fit_transform(docs)
        word_counts = np.asarray(wc_dtm.sum(axis=1)).ravel()

    # -- Step 6: assemble output DataFrame -----------------------------------
    result = pd.DataFrame(
        cat_counts,
        index=doc_index,
        columns=dx_expanded.columns,
    )

    if as_percentage:
        # Avoid division by zero for empty documents.
        safe_wc = np.where(word_counts > 0, word_counts, 1)
        result = result.div(safe_wc, axis=0) * 100

    if as_percentage and precision is not None:
        result = result.round(precision)

    result.insert(0, "WC", word_counts)
    logger.debug(
        "Counting complete: %d documents, %d categories, WC range %d–%d",
        len(result),
        dx.shape[1],
        word_counts.min() if len(word_counts) else 0,
        word_counts.max() if len(word_counts) else 0,
    )

    if not return_words:
        return result

    # -- Build word-level DataFrame -----------------------------------------
    word_result = _build_word_result(
        dtm, doc_index, vocab_tokens, word_counts, as_percentage, precision
    )
    return result, word_result
