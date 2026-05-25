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
    "fetch_norms_liwc2015",
    "fetch_norms_liwc22",
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


def fetch_norms_liwc2015() -> pd.DataFrame:
    """
    Fetch the LIWC2015 Descriptive Statistics and Norms table.

    LIWC2015 Descriptive Statistics and Norms
    Reference means and standard deviations for every LIWC2015 category
    across the reference corpora reported in the LIWC2015 technical
    manual.

    .. seealso::
        :func:`fetch_norms_liwc22` for the LIWC-22 norms table.

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
    fname = _pup.fetch("norms-liwc2015.xlsx")
    df = (
        pd.read_excel(fname, header=[0, 1], index_col=0)
        .rename_axis("Category", axis="index")
        .rename_axis(["Source", "Statistic"], axis="columns")
    )
    return df


def fetch_norms_liwc22() -> pd.DataFrame:
    """
    Fetch the LIWC-22 Descriptive Statistics and Norms table.

    Reference means and standard deviations for every LIWC-22 category
    across the corpora in the "Test Kitchen" reference set.

    .. seealso::
        :func:`fetch_norms_liwc2015` for the LIWC2015 norms table.

    Distributed on the
    `LIWC website psychometrics manuals page <https://www.liwc.app/help/psychometrics-manuals>`__.

    Direct link to downloaded file:
    `https://www.liwc.app/static/documents/LIWC-22.Descriptive.Statistics-Test.Kitchen.xlsx
    <https://www.liwc.app/static/documents/LIWC-22.Descriptive.Statistics-Test.Kitchen.xlsx>`__

    If used, cite the LIWC22 Psychometrics Manual:
    Boyd et al., 2022. The development and psychometric properties of LIWC-22.

    Returns
    -------
    :class:`pandas.DataFrame`
        :class:`~pandas.DataFrame` of the ``LIWC-22.Descriptive.Statistics-Test.Kitchen.xlsx`` file.
    """
    fname = _pup.fetch("norms-liwc22.xlsx")
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


def fetch_psychometrics_manual(version: str, table: str) -> pd.DataFrame:  # noqa: C901
    """
    Fetch a table from a LIWC Psychometrics Manual.

    Psychometrics Manual PDFs are distributed on the
    `LIWC Psychometrics page <https://www.liwc.app/help/psychometrics-manuals>`__,
    and tables were extracted from the PDF and uploaded to individual Zenodo repositories.

    - `LIWC1999 Psychometrics Manual tables <https://zenodo.org/record/11397665>`__
    - `LIWC2001 Psychometrics Manual tables <https://zenodo.org/record/11397668>`__
    - `LIWC2007 Psychometrics Manual tables <https://zenodo.org/record/11397671>`__
    - `LIWC2015 Psychometrics Manual tables <https://zenodo.org/record/11397674>`__
    - `LIWC-22 Psychometrics Manual tables <https://zenodo.org/record/11397677>`__

    If used, cite the appropriate Psychometrics Manual.
    Citation information is available on the
    `LIWC Psychometrics page <https://www.liwc.app/help/psychometrics-manuals>`__,

    Parameters
    ----------
    version : str
        The version of LIWC to fetch the table from.
        Valid options are:
        ``"LIWC1999"``, ``"LIWC2001"``, ``"LIWC2007"``, ``"LIWC2015"``, and ``"LIWC22"``.
    table : str
        The name of the table to fetch.
        Valid options are: ``"1"``, ``"2"``, and ``"3"``.

    Returns
    -------
    :class:`pandas.DataFrame`
        The requested table as a :class:`pandas.DataFrame`.
    """
    _AVAILABLE_VERSIONS = {"LIWC1999", "LIWC2001", "LIWC2007", "LIWC2015", "LIWC22"}
    _AVAILABLE_TABLES = {
        "LIWC1999": {"1", "2", "3"},
        "LIWC2001": {"1", "2", "3"},
        "LIWC2007": {"1", "2", "3", "4"},
        "LIWC2015": {"1", "2", "3", "4"},
        "LIWC22": {"1", "2", "3", "4", "A1"},
    }
    if not isinstance(version, str):
        raise TypeError(f"Version must be a string. Got {type(version)}.")
    if not isinstance(table, str):
        raise TypeError(f"Table name must be a string. Got {type(table)}.")
    if version not in _AVAILABLE_VERSIONS:
        raise ValueError(f"Invalid version: {version}. Valid options are {_AVAILABLE_VERSIONS}.")
    if table not in _AVAILABLE_TABLES[version]:
        raise ValueError(
            f"Invalid table name: {table}. Valid options are {_AVAILABLE_TABLES[version]}."
        )
    registry_name = f"manual-{version.lower()}-table{table}.tsv"
    fname = _pup.fetch(registry_name)
    fpath = Path(fname)
    if version in {"LIWC1999", "LIWC2001"} and table == "1":

        def _build(source_path: Path) -> pd.DataFrame:
            return (
                pd.read_csv(source_path, sep="\t", dtype={"# Words": "Int8"})
                .rename(
                    columns={
                        "Dimension": "name",
                        "Abbrev": "category",
                        "Examples": "examples",
                        "# Words": "n_words",
                        "Judge 1": "judge1",
                        "Judge 2": "judge2",
                    }
                )
                .assign(parent=lambda x: x["name"].where(x["category"].isna()).ffill())
                .dropna(subset=["category"])
                .set_index(["parent", "name"])
            )
    elif version in {"LIWC1999", "LIWC2001"} and table == "2":

        def _build(source_path: Path) -> pd.DataFrame:
            return (
                pd.read_csv(source_path, sep="\t", header=1, index_col=0, thousands=",")
                .drop(columns=["Totals"])
                .T.rename_axis("corpus")
                .rename(
                    columns={
                        "Number of files": "n_files",
                        "Number of writers/speakers": "n_authors",
                        "Number of words": "n_words",
                        "Number of studies": "n_studies",
                    }
                )
            )
    elif version in {"LIWC1999", "LIWC2001"} and table == "3":

        def _build(source_path: Path) -> pd.DataFrame:
            return (
                pd.read_csv(source_path, sep="\t")
                .rename(columns={"Dimension": "name"})
                .assign(parent=lambda x: x["name"].where(x["name"].str.isupper()).ffill())
                .dropna()
                .pipe(
                    lambda x: x.assign(
                        **x["Mean (sd)"]
                        .str.extract(r"(?P<Mean>[\d.]+)\s*\((?P<SD>[\d.]+)\)")
                        .astype(float)
                    )
                )
                .drop(columns=["Mean (sd)"])
                .set_index(["parent", "name"])
            )
    elif version == "LIWC2007" and table == "1":

        def _build(source_path: Path) -> pd.DataFrame:
            return (
                pd.read_csv(source_path, sep="\t", dtype={"Words in category": "Int8"})
                .assign(parent=lambda x: x["Category"].where(x["Abbrev"].isna()).ffill())
                .dropna(subset=["Abbrev"])
                .pipe(
                    lambda x: x.assign(
                        **x["Alpha: Binary/raw"]
                        .str.extract(r"(?P<alpha_binary>[\d.]+)/(?P<alpha_raw>[\d.]+)")
                        .astype(float)
                    )
                )
                .drop(columns=["Alpha: Binary/raw"])
                .rename(
                    columns={
                        "Category": "name",
                        "Abbrev": "category",
                        "Examples": "examples",
                        "Word in category": "n_words",
                        "Validity (judges)": "validity",
                    }
                )
                .set_index(["parent", "category"])
            )
    elif version == "LIWC2007" and table == "2":

        def _build(source_path: Path) -> pd.DataFrame:
            return (
                pd.read_csv(source_path, sep="\t", index_col=0, thousands=",")
                .T.rename_axis("corpus")
                .rename(columns=lambda x: x.replace("Total ", "n_"))
            )
    elif version == "LIWC2007" and table == "3":

        def _build(source_path: Path) -> pd.DataFrame:
            return (
                pd.read_csv(source_path, sep="\t")
                .assign(parent=lambda x: x["Category"].where(x["Novels"].isna()).ffill())
                .dropna(subset=["Novels"])
                .rename(columns={"Category": "category", "Grand Means": "Mean", "Mean SDs": "StD"})
                .set_index(["parent", "category"])
            )
    elif version == "LIWC2007" and table == "4":

        def _build(source_path: Path) -> pd.DataFrame:
            return (
                pd.read_csv(source_path, sep="\t", header=[0, 1], index_col=0)
                .rename_axis("name")
                .set_axis(
                    ["liwc2007_mean", "liwc2007_sd", "liwc2001_mean", "liwc2001_sd", "r"], axis=1
                )
            )
    elif version == "LIWC2015" and table == "1":

        def _build(source_path: Path) -> pd.DataFrame:
            return (
                pd.read_csv(source_path, sep="\t", na_values="-")
                .assign(
                    parent=lambda x: (
                        x["Category"].where(x["Abbrev"].isna()).ffill().fillna(x["Abbrev"])
                    )
                )
                .dropna(subset=["Abbrev"])
                .rename(
                    columns={
                        "Category": "name",
                        "Abbrev": "category",
                        "Example": "examples",
                        "Words in category": "n_words",
                        "Internal Consistency (Uncorrected alpha)": "alpha_uncorrected",
                        "Internal Consistency (Corrected alpha)": "alpha_corrected",
                    }
                )
                .set_index(["parent", "category"])
            )
    elif version == "LIWC2015" and table == "2":

        def _build(source_path: Path) -> pd.DataFrame:
            return (
                pd.read_csv(source_path, sep="\t", index_col=0, thousands=",", na_values="Unknown")
                .astype("Int32")
                .T.rename_axis("corpus")
                .rename(columns=lambda x: x.replace("Total ", "n_"))
            )
    elif version == "LIWC2015" and table == "3":

        def _build(source_path: Path) -> pd.DataFrame:
            return (
                pd.read_csv(source_path, sep="\t")
                .assign(parent=lambda x: x["Category"].where(x["Novels"].isna()).ffill())
                .dropna(subset=["Novels"])
                .rename(columns={"Category": "category", "Grand Means": "Mean", "Mean SDs": "StD"})
                .set_index(["parent", "category"])
            )
    elif version == "LIWC2015" and table == "4":

        def _build(source_path: Path) -> pd.DataFrame:
            return (
                pd.read_csv(source_path, sep="\t", thousands=",", na_values=["-"])
                .assign(
                    parent=lambda x: (
                        x["LIWC Dimension"]
                        .where(x["Output Label"].isna())
                        .ffill()
                        .fillna(x["Output Label"])
                    )
                )
                .dropna(subset=["Output Label"])
                .rename(
                    columns={
                        "LIWC Dimension": "name",
                        "Output Label": "category",
                        "LIWC2015 mean": "liwc2015_mean",
                        "LIWC2007 mean": "liwc2007_mean",
                        "LIWC 2015/2007 Correlation": "r",
                    }
                )
                .set_index(["parent", "category"])
            )

    elif version == "LIWC22" and table == "1":

        def _build(source_path: Path) -> pd.DataFrame:
            return (
                pd.read_csv(source_path, sep="\t")
                .replace({"Corpus": {"Overall mean": "Total"}})
                .pipe(
                    lambda x: x.assign(
                        **x["Word Count M (SD)"]
                        .str.extract(r"(?P<n_words_mean>\d+) \((?P<n_words_sd>\d+)\)")
                        .astype(int)
                    )
                )
                .drop(columns=["Word Count M (SD)"])
                .rename(columns={"Corpus": "corpus", "Description": "description"})
                .set_index("corpus")
                .reindex(columns=["n_words_mean", "n_words_sd", "description"])
            )
    elif version == "LIWC22" and table == "2":

        def _build(source_path: Path) -> pd.DataFrame:
            return (
                pd.read_csv(source_path, sep="\t", na_values=["-"])
                .assign(
                    parent=lambda x: (
                        x["Category"].where(x["Abbrev."].isna()).ffill().fillna(x["Abbrev."])
                    )
                )
                .dropna(subset=["Abbrev."])
                .rename(
                    columns={
                        "Category": "name",
                        "Abbrev.": "category",
                        "Description/Most frequently used exemplars": "examples",
                        "Words/Entries in category": "n_words",
                        "Internal Consistency: Cronbach's alpha": "alpha",
                        "Internal Consistency: KR-20": "kr20",
                    }
                )
                .set_index(["parent", "category"])
            )
    elif version == "LIWC22" and table == "3":

        def _build(source_path: Path) -> pd.DataFrame:
            _df = (
                pd.read_csv(source_path, sep="\t", skiprows=[1, 2], na_values=["mean", "SD"])
                .assign(parent=lambda x: x["Category"].where(x["Twitter"].isna()).ffill())
                .dropna(subset=["Twitter"])
                .rename(columns={"Category": "name"})
                .set_index(["parent", "name"])
            )
            columns = pd.Series(_df.columns).replace(r"^Unnamed: \d+", pd.NA, regex=True).ffill()
            _df.columns = pd.MultiIndex.from_product(
                (columns.unique(), ["mean", "sd"]), names=("corpus", "statistic")
            )
            return _df
    elif version == "LIWC22" and table == "4":

        def _build(source_path: Path) -> pd.DataFrame:
            return pd.read_csv(
                source_path,
                sep="\t",
                skiprows=3,
                names=["liwc22_mean", "liwc22_sd", "liwc2015_mean", "liwc2015_sd", "r"],
            )
    elif version == "LIWC22" and table == "A1":

        def _build(source_path: Path) -> pd.DataFrame:
            return (
                pd.read_csv(source_path, sep="\t", thousands=",")
                .rename(
                    columns={
                        "Corpus": "corpus",
                        "Description": "description",
                        "Test Kitchen N": "n_files",
                        "Years Written": "timeframe",
                        "Population N": "n_authors",
                    }
                )
                .set_index("corpus")
                .reindex(columns=["n_files", "n_authors", "timeframe", "description"])
            )
    else:
        raise ValueError(f"Unexpected version and table combination: {version}, {table}")
        # def _build(source_path: Path) -> pd.DataFrame:
        #     return pd.read_csv(source_path, sep="\t", **kwargs)
    df = _build(fpath)
    return df


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
