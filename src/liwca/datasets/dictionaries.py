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
from collections.abc import Callable
from pathlib import Path

import pandas as pd
import pooch

from ..io import create_dx, dx_schema, read_dx, write_dx
from ._common import AuthorizedZenodoDownloader, make_pup
from ._common import get_location as _get_location

__all__ = [
    "fetch_bigtwo",
    "fetch_emfd",
    "fetch_empath",
    "fetch_honor",
    "fetch_leeq",
    "fetch_mystical",
    "fetch_sleep",
    "fetch_threat",
    "fetch_wrad",
    "get_location",
    "path",
]

logger = logging.getLogger(__name__)

_pup = make_pup("dictionaries")


def get_location() -> Path:
    """Return the local cache directory used by the dictionary fetchers."""
    return _get_location(_pup)


def path(name: str, **kwargs) -> Path:
    """Return the local path to the cached ``.dicx`` for a named dictionary.

    Calls the corresponding ``fetch_<name>(**kwargs)`` to ensure the .dicx
    cache is populated, then returns the local path. Useful for handing off
    to tools that consume a .dicx file directly (e.g., the LIWC-22 CLI).

    Parameters
    ----------
    name : str
        Friendly dictionary name, matching one of the public ``fetch_<name>``
        functions (e.g., ``"sleep"``, ``"emfd"``, ``"bigtwo"``).
    **kwargs
        Forwarded to the underlying fetcher (e.g., ``version="b"`` for
        ``"bigtwo"``).

    Returns
    -------
    :class:`~pathlib.Path`
        Path to the cached ``.dicx`` file.

    Raises
    ------
    ValueError
        If ``name`` does not correspond to a known fetcher.
    NotImplementedError
        If ``name`` refers to a dictionary that is not yet cached as ``.dicx``
        (currently only ``"wrad"`` - continuous-valued dictionaries are not
        yet supported by the schema).

    Examples
    --------
    >>> from liwca.datasets import dictionaries
    >>> dictionaries.path("sleep")  # doctest: +SKIP
    PosixPath('.../dictionaries/sleep.dicx')
    >>> dictionaries.path("bigtwo", version="b")  # doctest: +SKIP
    PosixPath('.../dictionaries/bigtwo_b.dicx')
    """
    fetcher = globals().get(f"fetch_{name}")
    if fetcher is None:
        available = sorted(n.removeprefix("fetch_") for n in __all__ if n.startswith("fetch_"))
        raise ValueError(f"Unknown dictionary {name!r}; available: {available}")
    if name == "wrad":
        raise NotImplementedError("fetch_wrad has continuous values and is not yet cached as .dicx")
    fetcher(**kwargs)  # populate the cache
    if name == "bigtwo":
        cache_name = f"bigtwo_{kwargs.get('version', 'a')}.dicx"
    else:
        cache_name = f"{name}.dicx"
    return Path(_pup.path) / cache_name


# ---------------------------------------------------------------------------
# Pooch processor: parse a source file once, cache as .dicx
# ---------------------------------------------------------------------------


class BuildDicx:
    """Pooch processor that parses a source dictionary file and caches as .dicx.

    Sibling of :class:`liwca.datasets._common.CacheCsv` for the dictionaries
    module. On first run (``action`` is ``"download"`` or ``"update"``),
    ``build_fn`` is called on the downloaded source file and the resulting
    DataFrame is written via :func:`liwca.io.write_dx` as ``cache_name``
    (a ``.dicx`` file) next to the source. On subsequent runs
    (``action == "fetch"`` and the .dicx exists), the cached path is
    returned directly with no parsing or rewriting.

    Parameters
    ----------
    build_fn : callable
        Receives the downloaded source file as a :class:`~pathlib.Path` and
        returns a dictionary :class:`~pandas.DataFrame` (lowercase string
        index named ``"DicTerm"``, binary int8 columns named ``"Category"``).
    cache_name : str
        Filename for the cached .dicx; written alongside the source file.
    """

    def __init__(
        self,
        build_fn: Callable[[Path], pd.DataFrame],
        cache_name: str,
    ) -> None:
        self.build_fn = build_fn
        self.cache_name = cache_name

    def __call__(self, fname: str, action: str, pup: pooch.Pooch) -> str:
        cache_path = Path(fname).parent / self.cache_name
        if action == "fetch" and cache_path.exists():
            return str(cache_path)
        df = self.build_fn(Path(fname))
        write_dx(df, cache_path)
        return str(cache_path)


# ---------------------------------------------------------------------------
# Fetch functions
# ---------------------------------------------------------------------------


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
    _BIGTWO_VERSIONS = {"a", "b"}
    if version not in _BIGTWO_VERSIONS:
        raise ValueError(f"version must be one of {_BIGTWO_VERSIONS}; got {version!r}")
    dicx_path = _pup.fetch(
        f"bigtwo-{version}.dic",
        processor=BuildDicx(read_dx, f"bigtwo-{version}.dicx"),
    )
    return read_dx(dicx_path)


def fetch_emfd() -> pd.DataFrame:
    """
    Fetch the extended moral foundations 2.0 dictionary.

    See the `Moral Foundations Dictionary 2.0 OSF page <https://osf.io/ezn37>`__.
    """
    dicx_path = _pup.fetch("emfd.dic", processor=BuildDicx(read_dx, "emfd.dicx"))
    return read_dx(dicx_path)


def fetch_empath() -> pd.DataFrame:
    """
    Fetch the pre-built Empath dictionary.

    See the `Empath GitHub repository <https://github.com/Ejhfast/empath-client>`__
    for more details and the direct download file.

    `Direct download link
    <https://raw.githubusercontent.com/Ejhfast/empath-client/refs/heads/master/empath/data/categories.tsv>`__.
    """

    def _build(source_path: Path) -> pd.DataFrame:
        with open(source_path, "r") as f:
            # It's all tab-separated except one typo: "follows \tstatus"
            data = [x.strip().split("\t") for x in f.readlines()]
        categories = {x[0]: x[1:] for x in data}
        # Remove empty term
        categories = {cat: [term for term in terms if term] for cat, terms in categories.items()}
        return create_dx(categories)

    dicx_path = _pup.fetch("empath.tsv", processor=BuildDicx(_build, "empath.dicx"))
    return read_dx(dicx_path)


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
    dicx_path = _pup.fetch("honor.dic", processor=BuildDicx(read_dx, "honor.dicx"))
    return read_dx(dicx_path)


def fetch_leeq() -> pd.DataFrame:
    """
    Fetch the Lexicon for Evaluation of Education Quality (LEEQ).

    https://lit.eecs.umich.edu/downloads.html#Lexicon%20for%20Evaluation%20of%20Education%20Quality%20(LEEQ)

    See `GitHub repository <https://github.com/MichiganNLP/LEEQLexicon>`__ for more info.
    """

    def _build(source_path: Path) -> pd.DataFrame:
        ser = pd.read_csv(source_path, sep="\t", index_col="word").squeeze(axis=1)
        df = pd.crosstab(ser.index, ser).astype("int8")
        df = df.sort_index(axis=0).sort_index(axis=1)
        return df.rename_axis("DicTerm", axis=0).rename_axis("Category", axis=1)

    dicx_path = _pup.fetch("leeq.tsv", processor=BuildDicx(_build, "leeq.dicx"))
    return read_dx(dicx_path)


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

    def _build(source_path: Path) -> pd.DataFrame:
        df = pd.read_excel(
            source_path,
            sheet_name="List1",
            header=None,
            usecols=[0, 1],
            names=["DicTerm", "Mystical"],
            skiprows=79,
            index_col="DicTerm",
        )
        logger.debug("Read mystical dictionary: %d terms from %s", len(df), source_path)
        return df

    dicx_path = _pup.fetch("mystical.xlsx", processor=BuildDicx(_build, "mystical.dicx"))
    return read_dx(dicx_path)


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

    def _build(source_path: Path) -> pd.DataFrame:
        words = pd.read_table(source_path, skiprows=1, header=None).stack().dropna().tolist()
        # Some duplicates; autocorrected based on Table S1 of the original paper.
        words[words.index("Can't sleep")] = "Cant sleep"
        words[words.index("Couldn't sleep")] = "Couldnt sleep"
        words[words.index("Didn't sleep")] = "Didnt sleep"
        df = pd.Series(1, name="sleep", index=words).to_frame()
        logger.debug("Read sleep dictionary: %d terms from %s", len(df), source_path)
        return df

    dicx_path = _pup.fetch("sleep.tsv", processor=BuildDicx(_build, "sleep.dicx"))
    return read_dx(dicx_path)


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

    def _build(source_path: Path) -> pd.DataFrame:
        with open(source_path, encoding="utf-8") as f:
            words = f.read().splitlines()
        df = pd.Series(1, name="threat", index=words).to_frame()
        logger.debug("Read threat dictionary: %d terms from %s", len(df), source_path)
        return df

    dicx_path = _pup.fetch("threat.txt", processor=BuildDicx(_build, "threat.dicx"))
    return read_dx(dicx_path)


def fetch_wrad() -> pd.DataFrame:
    """
    Fetch the Weighted Referential Activity Dictionary (WRAD).

    See the `WRAD GitHub repository <https://github.com/DAAP/WRAD>`__ for more info.

    Citation:
    Bucci, W. & Maskit, B. (2006).
    A weighted dictionary for Referential Activity.
    In J.G. Shanahan, Y. Qu, & J. Wiebe (Eds.)
    Computing Attitude and Affect in Text;
    Dordrecht, The Netherlands: Springer; pp. 49-60.
    """
    fname = _pup.fetch("wrad.Wt")
    fpath = Path(fname)
    df = pd.read_csv(fpath, sep=" ", skiprows=11, names=["DicTerm", "ReferentialActivity"])
    return dx_schema.validate(df)


def _fetch_liwc2015() -> pd.DataFrame:
    """
    Fetch the LIWC2015 dictionary.

    .. note:: This is a restricted file that requires approved access.
    """

    def _build(source_path: Path) -> pd.DataFrame:
        df = pd.read_excel(source_path, skiprows=[0, 1, 2, 4]).rename_axis("Category", axis=1)
        df.columns = df.columns.str.split("\n").str[1]
        df.columns = pd.Series(df.columns).ffill()
        df = df.melt(value_name="DicTerm").dropna()
        df = df.sort_values(["Category", "DicTerm"]).set_index("Category")
        as_dict = df["DicTerm"].astype(str).groupby("Category").agg(list).to_dict()
        return create_dx(as_dict)

    dicx_path = _pup.fetch(
        "liwc2015.xlsx",
        downloader=AuthorizedZenodoDownloader(),
        processor=BuildDicx(_build, "liwc2015.dicx"),
    )
    return read_dx(dicx_path)


def _fetch_liwc22() -> pd.DataFrame:
    """
    Fetch the LIWC22 dictionary.

    .. note:: This is a restricted file that requires approved access.
    """

    def _build(source_path: Path) -> pd.DataFrame:
        df = pd.read_excel(source_path, skiprows=2).rename_axis("Category", axis=1)
        df.columns = pd.Series(df.columns).replace(r"^Unnamed: \d+$", pd.NA, regex=True).ffill()
        df = df.melt(value_name="DicTerm").dropna()
        df = df.sort_values(["Category", "DicTerm"]).set_index("Category")
        as_dict = df["DicTerm"].astype(str).groupby("Category").agg(list).to_dict()
        return create_dx(as_dict)

    dicx_path = _pup.fetch(
        "liwc22.xlsx",
        downloader=AuthorizedZenodoDownloader(),
        processor=BuildDicx(_build, "liwc22.dicx"),
    )
    return read_dx(dicx_path)


def _fetch_translated(fstem: str) -> pd.DataFrame:
    """
    Fetch a translated dictionary shared on the LIWC site.

    Dictionaries are available on the
    `LIWC dictionaries page <https://www.liwc.app/dictionaries>`__.

    .. note:: These dictionaries require login for access.
    """
    downloader = AuthorizedZenodoDownloader()
    processor = pooch.Unzip()
    fname = f"{fstem}.dicx"
    fnames = _pup.fetch("translated.zip", downloader=downloader, processor=processor)
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
    downloader = AuthorizedZenodoDownloader()
    processor = pooch.Unzip()
    fname = f"{fstem}.dicx"
    fnames = _pup.fetch("usermade.zip", downloader=downloader, processor=processor)
    fpaths = {Path(fn).name: Path(fn) for fn in fnames}
    fpath = fpaths[fname]
    dx = read_dx(fpath)
    return dx
