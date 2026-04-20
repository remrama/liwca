"""Remote LIWC-format dictionaries - per-dictionary fetch functions.

Each function downloads its dictionary to a local cache (if not already
present) and returns it as a :class:`~pandas.DataFrame`.  The cache location
defaults to the OS user cache directory
(``pooch.os_cache("liwca") / "dictionaries"``) and can be overridden by
setting the ``LIWCA_DATA_DIR`` environment variable - dictionaries are then
cached in ``$LIWCA_DATA_DIR/dictionaries/``.

Power users who want the raw local file path can call
``liwca.datasets.dictionaries._pup.fetch(filename)`` directly.
"""

from __future__ import annotations

import logging
import os
from importlib.resources import files as _files
from pathlib import Path

import pandas as pd
import pooch

from ...io import create_dx, dx_schema, read_dx

__all__ = [
    "fetch_bigtwo",
    "fetch_emfd",
    "fetch_honor",
    "fetch_mystical",
    "fetch_sleep",
    "fetch_threat",
]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pooch download registry
# ---------------------------------------------------------------------------

# Resolve LIWCA_DATA_DIR manually (instead of via pooch's env= kwarg) so each
# dataset category gets its own subfolder even when the user overrides the
# cache root - otherwise dictionaries, tables, and corpora would collide in a
# single flat directory.
_root = Path(os.environ.get("LIWCA_DATA_DIR") or pooch.os_cache("liwca"))
_pup = pooch.create(path=_root / "dictionaries", base_url="")
with open(str(_files("liwca.datasets.dictionaries").joinpath("registry.txt"))) as _f:
    _pup.load_registry(_f)


def _authorized_zenodo_downloader(**kwargs) -> pooch.HTTPDownloader:
    if (token := os.environ.get("ZENODO_TOKEN")) is None:
        raise OSError("A `ZENODO_TOKEN` with repository access must be set to fetch this file.")
    authorization = f"Bearer {token}"
    downloader = pooch.HTTPDownloader(headers={"Authorization": authorization}, **kwargs)
    return downloader


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
    >>> from liwca.datasets import dictionaries
    >>> dx = dictionaries.fetch_bigtwo()  # doctest: +SKIP
    >>> dx = dictionaries.fetch_bigtwo(version="b")  # doctest: +SKIP
    """
    if version not in _BIGTWO_VERSIONS:
        raise ValueError(f"version must be one of {list(_BIGTWO_VERSIONS)}; got {version!r}")
    return read_dx(_pup.fetch(_BIGTWO_VERSIONS[version]))


def fetch_emfd() -> pd.DataFrame:
    """
    Fetch the extended moral foundations 2.0 dictionary.

    See the `Moral Foundations Dictionary 2.0 OSF page <https://osf.io/ezn37>`__.
    """
    return read_dx(_pup.fetch("mfd2.0.dic"))


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
    >>> from liwca.datasets import dictionaries
    >>> dx = dictionaries.fetch_honor()  # doctest: +SKIP
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
    >>> from liwca.datasets import dictionaries
    >>> dx = dictionaries.fetch_mystical()  # doctest: +SKIP
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
    >>> from liwca.datasets import dictionaries
    >>> dx = dictionaries.fetch_sleep()  # doctest: +SKIP
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
    >>> from liwca.datasets import dictionaries
    >>> dx = dictionaries.fetch_threat()  # doctest: +SKIP
    >>> "accidents" in dx.index  # doctest: +SKIP
    True
    """
    path = _pup.fetch("threat.txt")
    with open(path, encoding="utf-8") as f:
        words = f.read().splitlines()
    df = pd.Series(1, name="threat", index=words).to_frame()
    logger.debug("Read threat dictionary: %d terms from %s", len(df), path)
    return dx_schema.validate(df)


def fetch_empath() -> pd.DataFrame:
    """
    Fetch the pre-build Empath dictionary.

    See the `Empath GitHub repository <https://github.com/Ejhfast/empath-client>`__
    for more details and the direct download file.

    `Direct download link
    <https://raw.githubusercontent.com/Ejhfast/empath-client/refs/heads/master/empath/data/categories.tsv>`__.
    """
    fname = _pup.fetch("categories.tsv")
    fpath = Path(fname)
    with open(fpath, "r") as f:
        data = [x.strip().split("\t") for x in f.readlines()]
    categories = {x[0]: x[1:] for x in data}
    dx = create_dx(categories)
    return dx


def _fetch_liwc2015() -> pd.DataFrame:
    """
    Fetch the LIWC2015 dictionary.

    .. note:: This is a restricted file that requires approved access.
    """
    fname = _pup.fetch("LIWC2015.xlsx", downloader=_authorized_zenodo_downloader())
    fpath = Path(fname)
    df = pd.read_excel(fpath, skiprows=[0, 1, 2, 4]).rename_axis("Category", axis=1)
    df.columns = df.columns.str.split("\n").str[1]
    df.columns = pd.Series(df.columns).ffill()
    df = df.melt(value_name="DicTerm").dropna()
    df = df.sort_values(["Category", "DicTerm"]).set_index("Category")
    as_dict = df["DicTerm"].astype(str).groupby("Category").agg(list).to_dict()
    dx = create_dx(as_dict)
    return dx


def _fetch_liwc22() -> pd.DataFrame:
    """
    Fetch the LIWC22 dictionary.

    .. note:: This is a restricted file that requires approved access.
    """
    fname = _pup.fetch("LIWC22.xlsx", downloader=_authorized_zenodo_downloader())
    fpath = Path(fname)
    df = pd.read_excel(fpath, skiprows=2).rename_axis("Category", axis=1)
    df.columns = pd.Series(df.columns).replace(r"^Unnamed: \d+$", pd.NA, regex=True).ffill()
    df = df.melt(value_name="DicTerm").dropna()
    df = df.sort_values(["Category", "DicTerm"]).set_index("Category")
    as_dict = df["DicTerm"].astype(str).groupby("Category").agg(list).to_dict()
    dx = create_dx(as_dict)
    return dx


def _fetch_translated(fstem: str) -> pd.DataFrame:
    """
    Fetch a translated dictionary shared on the LIWC site.

    Dictionaries are available on the
    `LIWC dictionaries page <https://www.liwc.app/dictionaries>`__.

    .. note:: These dictionaries require login for access.
    """
    downloader = _authorized_zenodo_downloader()
    processor = pooch.Unzip()
    fname = f"{fstem}.dicx"
    fnames = _pup.fetch("translations.zip", downloader=downloader, processor=processor)
    fpaths = {Path(fn).name: Path(fn) for fn in fnames}
    fpath = fpaths[fname]
    dx = read_dx(fpath)
    return dx


def _fetch_usermade(fstem: str) -> pd.DataFrame:
    """
    Fetch a user-made dictionary shared on the LIWC site.

    Dictionaries are available on the
    `LIWC dictionaries page <https://www.liwc.app/dictionaries>`__.

    .. note:: These dictionaries require login for access.
    """
    downloader = _authorized_zenodo_downloader()
    processor = pooch.Unzip()
    fname = f"{fstem}.dicx"
    fnames = _pup.fetch("user-made.zip", downloader=downloader, processor=processor)
    fpaths = {Path(fn).name: Path(fn) for fn in fnames}
    fpath = fpaths[fname]
    dx = read_dx(fpath)
    return dx
