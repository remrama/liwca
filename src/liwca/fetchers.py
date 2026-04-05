"""Remote LIWC-format dictionaries — per-dictionary fetch functions.

Each function downloads its dictionary to a local cache (if not already
present) and returns it as a :class:`~pandas.DataFrame`.  The cache location
defaults to the OS user cache directory (``pooch.os_cache("liwca")``) and can
be overridden with the ``LIWCA_DATA_DIR`` environment variable.

Power users who want the raw local file path can call
``fetchers._pup.fetch(filename)`` directly.
"""

from __future__ import annotations

import logging
from importlib.resources import files as _files

import pandas as pd
import pooch

from .io import dx_schema, read_dx

__all__ = [
    "fetch_bigtwo",
    "fetch_honor",
    "fetch_mystical",
    "fetch_sleep",
    "fetch_threat",
]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pooch download registry
# ---------------------------------------------------------------------------

_pup = pooch.create(path=pooch.os_cache("liwca"), base_url="", env="LIWCA_DATA_DIR")
with open(str(_files("liwca.data").joinpath("registry.txt"))) as _f:
    _pup.load_registry(_f)


# ---------------------------------------------------------------------------
# Fetch functions
# ---------------------------------------------------------------------------

_BIGTWO_VERSIONS = {"a": "bigtwo_a.dic", "b": "bigtwo_b.dic"}


def fetch_bigtwo(*, version: str = "a") -> pd.DataFrame:
    """
    Fetch the Big Two personality dimensions dictionary.

    Parameters
    ----------
    version : {"a", "b"}, default "a"
        Which dimension to load. Version ``"a"`` is agency; ``"b"`` is
        communion.

    Returns
    -------
    :class:`pandas.DataFrame`
        Dictionary with a single ``"agency"`` (version ``"a"``) or
        ``"communion"`` (version ``"b"``) category.

    Notes
    -----
    The Big Two (Agency and Communion) capture fundamental dimensions of social
    perception — how people evaluate themselves and others in terms of
    competence, assertiveness, and goal pursuit (agency) versus warmth,
    cooperation, and social connection (communion).

    Source: `OSF <https://osf.io/62txv>`__

    References
    ----------
    .. [1] TODO

    Examples
    --------
    >>> import liwca
    >>> dx = liwca.fetch_bigtwo()  # doctest: +SKIP
    >>> dx = liwca.fetch_bigtwo(version="b")  # doctest: +SKIP
    """
    if version not in _BIGTWO_VERSIONS:
        raise ValueError(f"version must be one of {list(_BIGTWO_VERSIONS)}; got {version!r}")
    return read_dx(_pup.fetch(_BIGTWO_VERSIONS[version]))


def fetch_honor() -> pd.DataFrame:
    """
    Fetch the honor culture dictionary.

    Returns
    -------
    :class:`pandas.DataFrame`
        Dictionary for detecting honor culture language.

    Notes
    -----
    Developed for research on cultural tightness-looseness and honor norms.

    Source: `Gelfand et al., 2015
    <https://drive.google.com/uc?export=download&id=1EmQ5fFcr7ATRffyIP87Fej_TO3nDER6h>`__

    References
    ----------
    .. [1] TODO

    Examples
    --------
    >>> import liwca
    >>> dx = liwca.fetch_honor()  # doctest: +SKIP
    """
    return read_dx(_pup.fetch("honor.dic"))


def fetch_mystical() -> pd.DataFrame:
    """
    Fetch the mystical experience dictionary.

    Returns
    -------
    :class:`pandas.DataFrame`
        Dictionary with a single ``"Mystical"`` category.

    Notes
    -----
    Captures language related to mystical experiences, such as transcendence,
    unity, and altered states of consciousness.

    Source: `OSF <https://osf.io/6ph8z>`__

    References
    ----------
    .. [1] TODO

    Examples
    --------
    >>> import liwca
    >>> dx = liwca.fetch_mystical()  # doctest: +SKIP
    """
    path = _pup.fetch("mystical.xlsx")
    df = pd.read_excel(
        path,
        sheet_name="List1",
        header=None,
        usecols=[0, 1],
        names=["DicTerm", "Mystical"],
        skiprows=79,
        index_col="DicTerm",
    )
    logger.debug("Read mystical dictionary: %d terms from %s", len(df), path)
    return dx_schema.validate(df)


def fetch_sleep() -> pd.DataFrame:
    """
    Fetch the sleep-related language dictionary.

    Returns
    -------
    :class:`pandas.DataFrame`
        Dictionary with a single ``"sleep"`` category.

    Notes
    -----
    Captures sleep-related language, originally developed for research on sleep
    disturbance and suicidal ideation in social media text.

    Source: `Zenodo <https://zenodo.org/records/13941010>`__

    References
    ----------
    .. [1] TODO

    Examples
    --------
    >>> import liwca
    >>> dx = liwca.fetch_sleep()  # doctest: +SKIP
    >>> "cant sleep" in dx.index  # doctest: +SKIP
    True
    """
    path = _pup.fetch("sleep.tsv")
    words = pd.read_table(path, skiprows=1, header=None).stack().dropna().tolist()
    # Some duplicates; autocorrected based on Table S1 of the original paper.
    words[words.index("Can't sleep")] = "Cant sleep"
    words[words.index("Couldn't sleep")] = "Couldnt sleep"
    words[words.index("Didn't sleep")] = "Didnt sleep"
    df = pd.Series(1, name="sleep", index=words).to_frame()
    logger.debug("Read sleep dictionary: %d terms from %s", len(df), path)
    return dx_schema.validate(df)


def fetch_threat() -> pd.DataFrame:
    """
    Fetch the threat perception dictionary.

    Returns
    -------
    :class:`pandas.DataFrame`
        Dictionary with a single ``"threat"`` category.

    Notes
    -----
    Developed for research on how ecological and historical threats shape
    cultural tightness across nations.

    Source: `Gelfand et al.
    <https://www.michelegelfand.com/threat-dictionary>`__

    References
    ----------
    .. [1] TODO

    Examples
    --------
    >>> import liwca
    >>> dx = liwca.fetch_threat()  # doctest: +SKIP
    >>> "accidents" in dx.index  # doctest: +SKIP
    True
    """
    path = _pup.fetch("threat.txt")
    with open(path, encoding="utf-8") as f:
        words = f.read().splitlines()
    df = pd.Series(1, name="threat", index=words).to_frame()
    logger.debug("Read threat dictionary: %d terms from %s", len(df), path)
    return dx_schema.validate(df)
