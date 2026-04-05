"""
Fetching and discovery of remote LIWC-format dictionaries.

Provides functions to list available dictionaries, retrieve metadata, and
download dictionary files via the Pooch caching layer.
"""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd
import pooch

from ._catalogue import _VERSION_MAP, CATALOGUE, DictInfo
from .io import dx_schema, read_dx

__all__ = [
    "DictInfo",
    "fetch_dx",
    "fetch_path",
    "get_dict_info",
    "list_available",
]


logger = logging.getLogger(__name__)

_pup = pooch.create(
    path=pooch.os_cache("liwca"),
    base_url="",
    env="LIWCA_DATA_DIR",
    registry={vi.filename: vi.hash for vi in _VERSION_MAP.values()},
    urls={vi.filename: vi.url for vi in _VERSION_MAP.values()},
)


def list_available() -> list[str]:
    """
    List the names of all dictionaries available for fetching.

    Returns
    -------
    list of :class:`str`
        Sorted list of dictionary names that can be passed to
        :func:`fetch_dx` or :func:`fetch_path`.

    Examples
    --------
    >>> import liwca
    >>> liwca.list_available()
    ['bigtwo', 'honor', 'mystical', 'sleep', 'threat']
    """
    return sorted(CATALOGUE)


def get_dict_info(dic_name: str) -> DictInfo:
    """
    Return metadata for a registered dictionary.

    Parameters
    ----------
    dic_name : :class:`str`
        The name of the dictionary (e.g., ``"threat"``).

    Returns
    -------
    :class:`DictInfo`
        Metadata for the dictionary.

    Raises
    ------
    ValueError
        If ``dic_name`` is not found in the catalogue.

    Examples
    --------
    >>> import liwca
    >>> info = liwca.get_dict_info("threat")
    >>> info.description
    'Threat perception dictionary (English).'
    """
    if dic_name not in CATALOGUE:
        raise ValueError(
            f"Dictionary '{dic_name}' not found. Available: {', '.join(sorted(CATALOGUE))}"
        )
    return CATALOGUE[dic_name]


def _resolve_version(dic_name: str, version: Optional[str]) -> Optional[str]:
    """Resolve and validate the version argument for a dictionary.

    Returns the version key to use in ``_VERSION_MAP``: ``None`` for
    non-versioned dictionaries, or a version string for versioned ones.
    """
    if dic_name not in CATALOGUE:
        raise ValueError(
            f"Dictionary '{dic_name}' not found. Available: {', '.join(sorted(CATALOGUE))}"
        )
    info = CATALOGUE[dic_name]
    if info.default_version is None:
        # Non-versioned dictionary
        if version is not None:
            raise ValueError(
                f"Dictionary '{dic_name}' is not versioned; do not pass a version argument."
            )
        return None
    # Versioned dictionary
    ver = version if version is not None else info.default_version
    if ver not in info.available_versions:
        raise ValueError(
            f"Version '{ver}' not available for '{dic_name}'. "
            f"Available: {', '.join(info.available_versions)}"
        )
    return ver


def fetch_path(dic_name: str, *, version: Optional[str] = None) -> str:
    """
    Fetch a remote dictionary file and return the local cached filepath.

    Downloads the file if it is not already cached locally.
    No processing or reading is performed on the file.

    Parameters
    ----------
    dic_name : :class:`str`
        The name of the dictionary to fetch (e.g., ``"threat"``).
    version : :class:`str`, optional
        Version to fetch for versioned dictionaries. Must be ``None`` for
        non-versioned dictionaries. If ``None`` and the dictionary is
        versioned, the default version is used.

    Returns
    -------
    :class:`str`
        The absolute path to the cached file.

    Raises
    ------
    ValueError
        If ``dic_name`` is not found in the catalogue, or if an invalid
        version is requested.

    Examples
    --------
    >>> import liwca
    >>> fp = liwca.fetch_path("threat")  # doctest: +SKIP
    """
    ver_key = _resolve_version(dic_name, version)
    vi = _VERSION_MAP[(dic_name, ver_key)]
    try:
        fp = _pup.fetch(vi.filename)
    except Exception as e:
        raise ValueError(f"Failed to download dictionary '{dic_name}': {e}") from e
    logger.debug("Fetched '%s' to %s", dic_name, fp)
    return str(fp)


def fetch_dx(dic_name: str, *, version: Optional[str] = None) -> pd.DataFrame:
    """
    Fetch a remote dictionary and load as a :class:`~pandas.DataFrame`.

    Downloads the raw file to local cache (if not already cached), reads it
    into a :class:`~pandas.DataFrame`, and validates it against the dictionary schema.

    Parameters
    ----------
    dic_name : :class:`str`
        The name of the dictionary to fetch.
    version : :class:`str`, optional
        Version to fetch for versioned dictionaries. Must be ``None`` for
        non-versioned dictionaries. If ``None`` and the dictionary is
        versioned, the default version is used.

    Returns
    -------
    :class:`pandas.DataFrame`
        The dictionary as a pandas :class:`~pandas.DataFrame`.

    Notes
    -----
    Downloaded files are cached locally so subsequent calls are fast. To
    customize the download directory, set the ``LIWCA_DATA_DIR`` environment
    variable before importing liwca:

    .. code-block:: bash

       export LIWCA_DATA_DIR=/path/to/my/cache

    Examples
    --------
    >>> import liwca
    >>> dx = liwca.fetch_dx("threat")
    >>> dx.head()  # doctest: +NORMALIZE_WHITESPACE
    Category     threat
    DicTerm
    accidents         1
    accusations       1
    advised           1
    afraid            1
    aftermath         1
    """
    fp = fetch_path(dic_name, version=version)

    info = CATALOGUE.get(dic_name)
    reader = info.reader if info else None
    suffix = Path(fp).suffix
    if reader is None and suffix not in (".dic", ".dicx"):
        raise ValueError(
            f"Dictionary '{dic_name}' has format '{suffix}' but no registered reader. "
            f"Supported fallback formats: .dic, .dicx"
        )
    try:
        df = reader(fp) if reader is not None else read_dx(fp)
    except Exception as e:
        raise ValueError(f"Error reading dictionary '{dic_name}': {e}") from e

    if reader is not None:
        df = dx_schema.validate(df)

    logger.debug("Successfully fetched '%s' (%d terms)", dic_name, len(df))
    return df
