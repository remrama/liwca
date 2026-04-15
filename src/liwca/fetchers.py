"""Remote LIWC-format dictionaries - per-dictionary fetch functions.

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
    Fetch the big two (agency and communion) dictionary.

    Parameters
    ----------
    version : {"a", "b"}, default "a"
        Which version to load.
        Version ``"a"`` is the "main" version (described in manuscript).
        Version ``"b"`` is the alternate version (described in Supplementary Information).

    Returns
    -------
    :class:`pandas.DataFrame`
        Dictionary with ``"agency"`` and ``"communion"`` categories.

    Notes
    -----
    This dictionary is described in Pietraszkiewicz et al.\\ [1]_
    and publicly available along with other resources on OSF\\ [2]_.

    References
    ----------
    .. [1] Pietraszkiewicz et al., 2019.
           The big two dictionaries: Capturing agency and communion in natural language.
           *European Journal of Social Psychology*
           doi:`10.1002/ejsp.2561 <https://doi.org/10.1002/ejsp.2561>`__
    .. [2] `https://osf.io/62txv <https://osf.io/62txv>`__

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
    Fetch the honor dictionary.

    Returns
    -------
    :class:`pandas.DataFrame`
        Dictionary for detecting honor language.

    Notes
    -----
    The honor dictionary is described in Gelfand et al.\\ [1]_
    and available, along with other resources, on Michele Gelfand's website\\ [2]_.

    References
    ----------
    .. [1] Gelfand et al., 2015.
           Culture and getting to yes:
           The linguistic signature of creative agreements in the United States and Egypt.
           *Journal of Organizational Behavior*
           doi:`10.1002/job.2026 <https://doi.org/10.1002/job.2026>`__
    .. [2] `https://www.michelegelfand.com/honor-dictionary <https://www.michelegelfand.com/honor-dictionary>`__

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
        Dictionary with a single ``"mystical"`` category.

    Notes
    -----
    The mystical experience dictionary is described in Žuljević et al.\\ [1]_
    and publicly available on OSF\\ [2]_.

    References
    ----------
    .. [1] Žuljević et al., 2024.
           Mystical and affective aspects of psychedelic use in a naturalistic setting:
           A linguistic analysis of online experience reports.
           *Journal of Psychoactive Drugs*
           doi:`10.1080/02791072.2023.2274382 <https://doi.org/10.1080/02791072.2023.2274382>`__
    .. [2] `https://osf.io/6ph8z <https://osf.io/6ph8z>`__

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
    Fetch the sleep dictionary.

    Returns
    -------
    :class:`pandas.DataFrame`
        Dictionary with a single ``"sleep"`` category.

    Notes
    -----
    The sleep dictionary is described in Ladis et al.\\ [1]_
    and is publicly available on Zenodo\\ [2]_.

    There is also a full version in the Supplementary Information file of the
    original publication that has not been converted to the publicly accessible tables yet.

    References
    ----------
    .. [1] Ladis et al., 2023.
           Inferring sleep disturbance from text messages of suicide attempt survivors:
           A pilot study.
           *Suicide and Life-Threatening Behavior*
           doi:`10.1111/sltb.12920 <https://doi.org/10.1111/sltb.12920>`__
    .. [2] `https://zenodo.org/records/13941010 <https://zenodo.org/records/13941010>`__

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
    Fetch the threat dictionary.

    Returns
    -------
    :class:`pandas.DataFrame`
        Dictionary with a single ``"threat"`` category.

    Notes
    -----
    The threat dictionary is described in Choi et al.\\ [1]_
    and available, along with other resources, on Michele Gelfand's website\\ [2]_.

    References
    ----------
    .. [1] Choi et al., 2022.
           When danger strikes:
           A linguistic tool for tracking America's collective response to threats.
           *Proceedings of the National Academy of Sciences*
           doi:`10.1073/pnas.2113891119 <https://doi.org/10.1073/pnas.2113891119>`__
    .. [2] `https://www.michelegelfand.com/threat-dictionary <https://www.michelegelfand.com/threat-dictionary>`__

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
