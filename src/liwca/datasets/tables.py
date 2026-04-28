"""Remote published tables (norms, descriptive statistics, etc.) - per-table fetch functions.

Each function downloads its table to a local cache (if not already
present) and returns a :class:`pathlib.Path` to the downloaded file.
The cache location defaults to
``pooch.os_cache("liwca") / "tables"`` and can be overridden by
setting the ``LIWCA_DATA_DIR`` environment variable - tables are
then cached in ``$LIWCA_DATA_DIR/tables/``.

Power users who want the raw local file path can call
``liwca.datasets.tables._pup.fetch(filename)`` directly.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from ._common import get_location as _get_location
from ._common import make_pup

__all__ = [
    "fetch_liwc2015norms",
    "fetch_liwc22norms",
    "fetch_psychnorms",
    "fetch_scope",
    "get_location",
]

logger = logging.getLogger(__name__)

_pup = make_pup("tables")


def get_location() -> Path:
    """Return the local cache directory used by the table fetchers."""
    return _get_location(_pup)


# ---------------------------------------------------------------------------
# Fetch functions
# ---------------------------------------------------------------------------


def fetch_liwc2015norms() -> pd.DataFrame:
    """
    Fetch the LIWC2015 Descriptive Statistics and Norms table.

    LIWC2015 Descriptive Statistics and Norms
    Reference means and standard deviations for every LIWC2015 category
    across the reference corpora reported in the LIWC2015 technical
    manual.

    .. seealso::
        :func:`fetch_liwc22norms` for the LIWC-22 norms table.

    Distributed on the
    `LIWC website psychometrics manuals page <https://www.liwc.app/help/psychometrics-manuals>`__.

    Direct link to downloaded file:
    `https://www.liwc.app/static/documents/LIWC2015.Descriptive.Statistics.Full.xlsx
    <https://www.liwc.app/static/documents/LIWC2015.Descriptive.Statistics.Full.xlsx>`__

    If used, cite the LIWC2015 Psychometrics Manual:
    Pennebaker et al., 2015. The development and psychometric properties of LIWC2015.
    doi:`10.15781/T29G6Z <https://doi.org/10.15781/T29G6Z>`__

    Returns
    -------
    :class:`pandas.DataFrame`
        :class:`~pandas.DataFrame` of the ``LIWC2015.Descriptive.Statistics.Full.xlsx`` file.
    """
    fname = _pup.fetch("liwc2015-norms.xlsx")
    df = (
        pd.read_excel(fname, header=[0, 1], index_col=0)
        .rename_axis("Category", axis="index")
        .rename_axis(["Source", "Statistic"], axis="columns")
    )
    return df


def fetch_liwc22norms() -> pd.DataFrame:
    """
    Fetch the LIWC-22 Descriptive Statistics and Norms table.

    Reference means and standard deviations for every LIWC-22 category
    across the corpora in the "Test Kitchen" reference set.

    .. seealso::
        :func:`fetch_liwc2015norms` for the LIWC2015 norms table.

    Distributed on the
    `LIWC website psychometrics manuals page <https://www.liwc.app/help/psychometrics-manuals>`__.

    Direct link to downloaded file:
    `https://www.liwc.app/static/documents/LIWC-22.Descriptive.Statistics-Test.Kitchen.xlsx
    <https://www.liwc.app/static/documents/LIWC-22.Descriptive.Statistics-Test.Kitchen.xlsx>`__

    If used, cite the LIWC2015 Psychometrics Manual:
    Boyd et al., 2022. The development and psychometric properties of LIWC-22.

    Returns
    -------
    :class:`pandas.DataFrame`
        :class:`~pandas.DataFrame` of the ``LIWC-22.Descriptive.Statistics-Test.Kitchen.xlsx`` file.
    """
    fname = _pup.fetch("liwc22-norms.xlsx")
    df = (
        pd.read_excel(fname, header=[0, 1], index_col=0)
        .rename_axis("Category", axis="index")
        .rename_axis(["Source", "Statistic"], axis="columns")
    )
    return df


def fetch_psychnorms() -> pd.DataFrame:
    """
    Fetch the psychNorms column-classification metadata table.

    The returned :class:`~pandas.DataFrame` describes each of the ~290
    psycholinguistic norms aggregated in psychNorms - one row per norm,
    columns ``norm``, ``description``, ``citation``, ``category``,
    ``source``. For per-norm lexicon access (the actual word-level scores
    sliced into a weighted ``.dicx``), use
    :func:`liwca.datasets.dictionaries.fetch_psychnorms`.

    Distributed on the `psychNorms GitHub repository <https://github.com/Zak-Hussain/psychNorms>`__.

    If used, cite:
    Hussain et al., 2024.
    Probing the contents of semantic representations from text, behavior, and brain data
    using the psychNorms metabase. *arXiv*
    doi:`10.48550/arXiv.2412.04936 <https://doi.org/10.48550/arXiv.2412.04936>`__

    See Also
    --------
    liwca.datasets.dictionaries.fetch_psychnorms :
        Fetch one psychNorms norm as a weighted ``.dicx`` dictionary.
    liwca.datasets.dictionaries.list_psychnorms_stems :
        List the valid stems accepted by ``dictionaries.fetch_psychnorms``.
    """
    fname = _pup.fetch("psychnorms-metadata.csv")
    return pd.read_csv(fname)


def fetch_scope() -> pd.DataFrame:
    """
    Fetch the SCOPE column-classification metadata table.

    The returned :class:`~pandas.DataFrame` describes each variable in the
    `South CarOlina Psycholinguistic metabase (SCOPE)
    <https://sc.edu/study/colleges_schools/artsandsciences/psychology/research_clinical_facilities/scope/>`__,
    one row per variable, with hierarchical ``Level.1`` / ``Level.2`` /
    ``Level3.`` grouping plus ``Source``, ``Definition``, ``Citation``, and
    ``Web.Link`` columns. For per-column lexicon access (the actual
    word-level scores sliced into a weighted ``.dicx``), use
    :func:`liwca.datasets.dictionaries.fetch_scope`.

    SCOPE is a curated collection of psycholinguistic properties of words
    from major databases - more than 250 variables and over 100,000 words
    plus ~80,000 nonwords.

    Direct link to downloaded file:
    `https://sc.edu/scopedb/fulldb/data_with_metadata.xlsx
    <https://sc.edu/scopedb/fulldb/data_with_metadata.xlsx>`__.

    If used, cite:
    Gao et al., 2023. SCOPE: The South Carolina psycholinguistic metabase. *Behav Res Methods*
    doi:`10.3758/s13428-022-01934-0 <https://doi.org/10.3758/s13428-022-01934-0>`__

    See Also
    --------
    liwca.datasets.dictionaries.fetch_scope :
        Fetch one SCOPE variable as a weighted ``.dicx`` dictionary.
    liwca.datasets.dictionaries.list_scope_stems :
        List the valid stems accepted by ``dictionaries.fetch_scope``.
    """
    fname = _pup.fetch("scope.xlsx")
    return pd.read_excel(fname, sheet_name="metadata")
