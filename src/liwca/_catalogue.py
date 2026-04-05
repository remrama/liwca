"""
Dictionary catalogue — single source of truth for all registered dictionaries.

Each dictionary has a :class:`DictInfo` entry in :data:`CATALOGUE` containing
metadata (description, source, citation) and an optional reader callable for
non-standard file formats.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Optional

import pandas as pd

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

__all__ = ["CATALOGUE", "DictInfo"]


@dataclass(frozen=True)
class DictInfo:
    """Metadata for a registered LIWC-format dictionary.

    Parameters
    ----------
    description : str
        Short human-readable description of the dictionary.
    format : str
        File extension (e.g., ``".dic"``, ``".xlsx"``).
    source_url : str
        URL to the dictionary source (project page or download).
    source_label : str
        Display label for the source link (e.g., ``"OSF"``, ``"Zenodo"``).
    detail : str
        Longer description paragraph for documentation.
    examples : tuple of str
        Example terms from the dictionary, used in documentation and validated
        by tests. Terms should be lowercase (as stored in the dictionary).
    language : str
        Language of the dictionary (default ``"English"``).
    citation : str
        Optional citation identifier (e.g., ``"PMC9908817"``).
    citation_url : str
        Optional URL for the citation.
    reader : callable, optional
        Reader function ``(filepath) -> DataFrame`` for non-standard formats.
        ``None`` means the standard ``.dic`` / ``.dicx`` reader is used.
    """

    description: str
    format: str
    source_url: str
    source_label: str
    detail: str = ""
    examples: tuple[str, ...] = ()
    language: str = "English"
    citation: str = ""
    citation_url: str = ""
    reader: Optional[Callable[[str], pd.DataFrame]] = field(default=None, repr=False)


# ---------------------------------------------------------------------------
# Reader functions for non-standard remote dictionary formats
# ---------------------------------------------------------------------------


def _read_raw_sleep(fname: str) -> pd.DataFrame:
    """Read the raw sleep dictionary TSV file.

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


def _read_raw_threat(fname: str) -> pd.DataFrame:
    """Read the raw threat dictionary text file.

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


def _read_raw_mystical(fname: str) -> pd.DataFrame:
    """Read the raw mystical dictionary Excel file.

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


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------

CATALOGUE: dict[str, DictInfo] = {
    "bigtwo_a": DictInfo(
        description="Big Two personality dimensions (agency).",
        format=".dic",
        source_url="https://osf.io/download/62txv",
        source_label="OSF",
        detail=(
            "Agency dimension of the Big Two personality framework. The Big Two"
            " (Agency and Communion) capture fundamental dimensions of social"
            " perception — how people evaluate themselves and others in terms of"
            " competence, assertiveness, and goal pursuit (agency) versus warmth,"
            " cooperation, and social connection (communion)."
        ),
    ),
    "bigtwo_b": DictInfo(
        description="Big Two personality dimensions (communion).",
        format=".dic",
        source_url="https://osf.io/download/y59eb",
        source_label="OSF",
        detail=(
            "Communion dimension of the Big Two personality framework. Captures"
            " language related to warmth, morality, and social connection. See"
            " ``bigtwo_a`` for the complementary agency dimension."
        ),
    ),
    "honor": DictInfo(
        description="Honor culture dictionary (English).",
        format=".dic",
        source_url="https://drive.google.com/uc?export=download&id=1EmQ5fFcr7ATRffyIP87Fej_TO3nDER6h",
        source_label="Gelfand et al., 2015",
        detail=(
            "Dictionary for detecting honor culture language, developed for"
            " research on cultural tightness-looseness and honor norms."
        ),
    ),
    "mystical": DictInfo(
        description="Mystical experience dictionary.",
        format=".xlsx",
        source_url="https://osf.io/6ph8z",
        source_label="OSF",
        detail=(
            "Dictionary for identifying language related to mystical experiences,"
            " such as transcendence, unity, and altered states of consciousness."
        ),
        reader=_read_raw_mystical,
    ),
    "sleep": DictInfo(
        description="Sleep-related language dictionary.",
        format=".tsv",
        source_url="https://zenodo.org/records/13941010",
        source_label="Zenodo",
        detail=(
            "Dictionary capturing sleep-related language, originally developed"
            " for research on sleep disturbance and suicidal ideation in social"
            " media text."
        ),
        examples=("cant sleep", "couldnt sleep", "didnt sleep"),
        citation="PMC9908817",
        citation_url="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9908817",
        reader=_read_raw_sleep,
    ),
    "threat": DictInfo(
        description="Threat perception dictionary (English).",
        format=".txt",
        source_url="https://www.michelegelfand.com/threat-dictionary",
        source_label="Gelfand et al.",
        detail=(
            "Dictionary for measuring perceived societal threat, developed for"
            " research on how ecological and historical threats shape cultural"
            " tightness across nations."
        ),
        examples=("accidents", "accusations", "afraid", "aftermath"),
        citation="doi:10.1073/pnas.2113891119",
        citation_url="https://doi.org/10.1073/pnas.2113891119",
        reader=_read_raw_threat,
    ),
}
