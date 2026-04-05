"""
Dictionary catalogue — single source of truth for all registered dictionaries.

Metadata and download info are stored in ``data/registry.json``. This module
loads that file at import time and builds :data:`CATALOGUE` (public metadata)
and :data:`_VERSION_MAP` (internal file-level info used by :mod:`liwca.io`).
"""

from __future__ import annotations

import json
import logging
from collections import namedtuple
from dataclasses import dataclass, field
from importlib.resources import files
from typing import Any, Callable, Optional

import pandas as pd

logger = logging.getLogger(__name__)

__all__ = ["CATALOGUE", "DictInfo"]


# ---------------------------------------------------------------------------
# Public dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DictInfo:
    """Metadata for a registered LIWC-format dictionary.

    Parameters
    ----------
    description : str
        Short human-readable description of the dictionary.
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
    default_version : str or None
        Default version string for versioned dictionaries, or ``None`` for
        non-versioned dictionaries.
    available_versions : tuple of str
        Version strings available for this dictionary. Empty tuple for
        non-versioned dictionaries.
    reader : callable, optional
        Reader function ``(filepath) -> DataFrame`` for non-standard formats.
        ``None`` means the standard ``.dic`` / ``.dicx`` reader is used.
    """

    description: str
    source_url: str
    source_label: str
    detail: str = ""
    examples: tuple[str, ...] = ()
    language: str = "English"
    citation: str = ""
    citation_url: str = ""
    default_version: Optional[str] = None
    available_versions: tuple[str, ...] = ()
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
# Reader name → callable mapping
# ---------------------------------------------------------------------------

_READERS: dict[str, Callable[[str], pd.DataFrame]] = {
    "_read_raw_sleep": _read_raw_sleep,
    "_read_raw_threat": _read_raw_threat,
    "_read_raw_mystical": _read_raw_mystical,
}

# ---------------------------------------------------------------------------
# Internal version info
# ---------------------------------------------------------------------------

_VersionInfo = namedtuple("_VersionInfo", ["filename", "hash", "url"])

# ---------------------------------------------------------------------------
# Load registry.json and build CATALOGUE + _VERSION_MAP
# ---------------------------------------------------------------------------

_registry_path = files("liwca.data").joinpath("registry.json")
with open(str(_registry_path), encoding="utf-8") as _f:
    _RAW_REGISTRY: dict[str, dict[str, Any]] = json.load(_f)

CATALOGUE: dict[str, DictInfo] = {}
_VERSION_MAP: dict[tuple[str, str | None], _VersionInfo] = {}

for _name, _entry in _RAW_REGISTRY.items():
    # Detect flat vs versioned by presence of "versions" key
    _is_versioned = "versions" in _entry

    # Resolve reader callable
    _reader_name = _entry.get("reader")
    _reader = _READERS[_reader_name] if _reader_name else None

    if _is_versioned:
        _versions = _entry["versions"]
        _default_ver = _entry["default_version"]
        _available = tuple(sorted(_versions))
        for _ver, _vdata in _versions.items():
            _VERSION_MAP[(_name, _ver)] = _VersionInfo(
                filename=_vdata["filename"],
                hash=_vdata["hash"],
                url=_vdata["url"],
            )
    else:
        _default_ver = None
        _available = ()
        _VERSION_MAP[(_name, None)] = _VersionInfo(
            filename=_entry["filename"],
            hash=_entry["hash"],
            url=_entry["url"],
        )

    CATALOGUE[_name] = DictInfo(
        description=_entry["description"],
        source_url=_entry["source_url"],
        source_label=_entry["source_label"],
        detail=_entry.get("detail", ""),
        examples=tuple(_entry.get("examples", ())),
        language=_entry.get("language", "English"),
        citation=_entry.get("citation", ""),
        citation_url=_entry.get("citation_url", ""),
        default_version=_default_ver,
        available_versions=_available,
        reader=_reader,
    )

# Validate no duplicate filenames — Pooch uses filenames as cache keys,
# so duplicates would cause silent overwrites.
_all_filenames = [vi.filename for vi in _VERSION_MAP.values()]
_seen: dict[str, tuple[str, str | None]] = {}
for _key, _vi in _VERSION_MAP.items():
    if _vi.filename in _seen:
        _prev = _seen[_vi.filename]
        raise ValueError(
            f"Duplicate filename '{_vi.filename}' in registry.json: "
            f"used by {_prev} and {_key}. "
            f"Each version must have a unique filename."
        )
    _seen[_vi.filename] = _key
