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
import pooch

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
    Fetch the psychNorms metabase table.

    Distributed on the `psychNorms GitHub repository <https://github.com/Zak-Hussain/psychNorms>`__.

    If used, cite:
    Hussain et al., 2024.
    Probing the contents of semantic representations from text, behavior, and brain data
    using the psychNorms metabase. *arXiv*
    doi:`10.48550/arXiv.2412.04936 <https://doi.org/10.48550/arXiv.2412.04936>`__
    """
    fnames = _pup.fetch("psychnorms.zip", processor=pooch.Unzip())
    fname = _pup.fetch("psychnorms_metadata.csv")
    fnames.append(fname)
    fpaths = {Path(fn).name: Path(fn) for fn in fnames}
    fpath = fpaths["psychNorms.csv"]
    # fpath = fpaths["psychNorms_metadata.csv"]
    df = pd.read_csv(fpath, low_memory=False)
    return df


def fetch_scope() -> pd.DataFrame:
    """
    Fetch the South Carolina Psycholinguistic Metabase (SCOPE).

    The `South CarOlina Psycholinguistic metabase (SCOPE)
    <https://sc.edu/study/colleges_schools/artsandsciences/psychology/research_clinical_facilities/scope/>`__
    is a curated collection of psycholinguistic properties of words from major databases.
    It contains more than 250 variables and over 100,000 words and 81,000 nonwords.

    Direct link to downloaded file:
    `https://sc.edu/scopedb/fulldb/data_with_metadata.xlsx
    <https://sc.edu/scopedb/fulldb/data_with_metadata.xlsx>`__.

    If used, cite:
    Gao et al., 2023. SCOPE: The South Carolina psycholinguistic metabase. *Behav Res Methods*
    doi:`10.3758/s13428-022-01934-0 <https://doi.org/10.3758/s13428-022-01934-0>`__
    """
    # fname1 = _pup.fetch("scope.csv")
    # fname2 = _pup.fetch("scope-metadata.csv")
    # fnames = [fname1, fname2]
    # fpaths = {Path(fn).name: Path(fn) for fn in fnames}
    # if read:
    #     df = pd.read_csv(fpaths["scope.csv"])
    #     return df
    # return fpaths
    fname = _pup.fetch("scope.xlsx")
    fpath = Path(fname)
    # df = pd.read_excel(fpath,
    #     sheet_name="metadata",
    #     engine="openpyxl",
    #     engine_kwargs={"read_only": True},
    #     usecols="A:S",
    #     nrows=271,
    # )
    df = pd.read_excel(fpath, sheet_name="data", engine="calamine")
    # fpath,
    # dtype=float,
    # sheet_name="data",
    # engine="calamine",
    # nrows=187929,
    # usecols="B:CR,CT:GB,GG:HH,HJ:JL",
    # usecols="A:JM",
    # "CS", # IPA, weird encodings, str
    # "GC:GF"  # vectors
    # "HI", # weird 1-2-1
    # "JM", # categorical string
    # "A",  # string
    # )
    return df
