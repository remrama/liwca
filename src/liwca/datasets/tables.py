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

from ._common import make_pup

__all__ = [
    "fetch_liwc2015norms",
    "fetch_liwc22norms",
    "fetch_psychnorms",
    "fetch_scope",
]

logger = logging.getLogger(__name__)

_pup = make_pup("tables")


# ---------------------------------------------------------------------------
# Fetch functions
# ---------------------------------------------------------------------------


def fetch_liwc2015norms() -> pd.DataFrame:
    """
    Fetch the LIWC-2015 descriptive statistics norms table.

    Reference means and standard deviations for every LIWC-2015 category
    across the reference corpora reported in the LIWC-2015 technical
    manual.

    Returns
    -------
    :class:`pandas.DataFrame`
        Local path to the downloaded
        ``LIWC2015.Descriptive.Statistics.Full.xlsx`` file.

    Notes
    -----
    Distributed on the LIWC website\\ [1]_.

    References
    ----------
    .. [1] TBD
    """
    fname = _pup.fetch("LIWC2015-norms.xlsx")
    df = (
        pd.read_excel(fname, header=[0, 1], index_col=0)
        .rename_axis("Category", axis="index")
        .rename_axis(["Source", "Statistic"], axis="columns")
    )
    return df


def fetch_liwc22norms() -> pd.DataFrame:
    """
    Fetch the LIWC-22 descriptive statistics ("Test Kitchen" norms) table.

    Reference means and standard deviations for every LIWC-22 category
    across the corpora in the "Test Kitchen" reference set.

    Returns
    -------
    :class:`pandas.DataFrame`
        Local path to the downloaded
        ``LIWC-22.Descriptive.Statistics-Test.Kitchen.xlsx`` file.

    Notes
    -----
    Distributed on the LIWC website\\ [1]_.

    References
    ----------
    .. [1] TBD
    """
    fname = _pup.fetch("LIWC22-norms.xlsx")
    df = (
        pd.read_excel(fname, header=[0, 1], index_col=0)
        .rename_axis("Category", axis="index")
        .rename_axis(["Source", "Statistic"], axis="columns")
    )
    return df


def fetch_psychnorms() -> pd.DataFrame:
    """
    Fetch the psychNorms table.

    See the `psychNorms GitHub repository <https://github.com/Zak-Hussain/psychNorms>`__.

    https://arxiv.org/abs/2412.04936
    """
    fnames = _pup.fetch("psychNorms.zip", processor=pooch.Unzip())
    fname = _pup.fetch("psychNorms_metadata.csv")
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

    Citation:
    Gao et al., 2023.
    SCOPE: The South Carolina psycholinguistic metabase.
    *Behav Res Methods*
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
