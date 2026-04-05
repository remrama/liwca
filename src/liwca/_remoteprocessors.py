"""
Reader functions for non-standard remote dictionary formats.

Each function takes a filepath and returns a DataFrame with dictionary terms
as the index and categories as columns with binary (0/1) values.
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)

__all__ = [
    "READERS",
    "read_raw_mystical",
    "read_raw_sleep",
    "read_raw_threat",
]


def read_raw_sleep(fname: str) -> pd.DataFrame:
    """
    Read/parse the Sleep LIWC dictionary.

    Dictionary details
    ^^^^^^^^^^^^^^^^^^
    * OSF repository: https://osf.io/9f3v2
    * Full table: https://osf.io/8hfcs
    * Paper: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9908817
    * Paper: https://onlinelibrary.wiley.com/doi/10.1111/sltb.12920

    Parameters
    ----------
    fname : str
        Path to the raw TSV file.

    Returns
    -------
    :class:`pandas.DataFrame`
        Dictionary DataFrame with a single ``"sleep"`` category.
    """
    words = pd.read_table(fname, skiprows=1, header=None).stack().dropna().tolist()
    # Some duplicates, and based on SI table I think they were autocorrected during publication.
    # Replacing with values from Table S1 (in most cases, otherwise inferred bc term was added)
    words[words.index("Can't sleep")] = "Cant sleep"  # from Table S1
    words[words.index("Couldn't sleep")] = "Couldnt sleep"  # inferred
    words[words.index("Didn't sleep")] = "Didnt sleep"  # inferred
    dx = pd.Series(1, name="sleep", index=words).to_frame()
    logger.debug("Read sleep dictionary: %d terms from %s", len(dx), fname)
    return dx


def read_raw_threat(fname: str) -> pd.DataFrame:
    """
    Read/parse the Threat LIWC dictionary.

    Dictionary details
    ^^^^^^^^^^^^^^^^^^
    * **Name:** ``threat``
    * **Language:** English
    * **Source:** https://www.michelegelfand.com/threat-dictionary
    * **Citation:** `doi:10.1073/pnas.2113891119 <https://doi.org/10.1073/pnas.2113891119>`_

    Parameters
    ----------
    fname : str
        Path to the raw text file (one word per line).

    Returns
    -------
    :class:`pandas.DataFrame`
        Dictionary DataFrame with a single ``"threat"`` category.
    """
    with open(fname, "r", encoding="utf-8") as f:
        words = f.read().splitlines()
    dx = pd.Series(1, name="threat", index=words).to_frame()
    logger.debug("Read threat dictionary: %d terms from %s", len(dx), fname)
    return dx


def read_raw_mystical(fname: str) -> pd.DataFrame:
    """
    Read/parse the Mystical LIWC dictionary.

    Dictionary details
    ^^^^^^^^^^^^^^^^^^
    * OSF repo: https://osf.io/6ph8z

    Parameters
    ----------
    fname : str
        Path to the raw Excel file.

    Returns
    -------
    :class:`pandas.DataFrame`
        Dictionary DataFrame with a single ``"Mystical"`` category.
    """
    df = pd.read_excel(
        fname,
        sheet_name="List1",
        header=None,
        usecols=[0, 1],
        names=["DicTerm", "Mystical"],
        skiprows=79,
        index_col="DicTerm",
    )
    logger.debug("Read mystical dictionary: %d terms from %s", len(df), fname)
    return df


READERS = {
    "sleep": read_raw_sleep,
    "threat": read_raw_threat,
    "mystical": read_raw_mystical,
}
