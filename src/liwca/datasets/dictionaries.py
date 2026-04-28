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

import json
import logging
from collections.abc import Callable
from pathlib import Path

import pandas as pd
import pooch

from ..io import (
    create_dx,
    read_dic,
    read_dicx,
    read_dicx_weighted,
    write_dicx,
    write_dicx_weighted,
)
from ._common import AuthorizedZenodoDownloader, make_pup
from ._common import get_location as _get_location

__all__ = [
    "fetch_bigtwo",
    "fetch_emfd",
    "fetch_empath",
    "fetch_hedonometer",
    "fetch_honor",
    "fetch_leeq",
    "fetch_mystical",
    "fetch_psychnorms",
    "fetch_scope",
    "fetch_sleep",
    "fetch_threat",
    "fetch_wrad",
    "get_location",
    "list_psychnorms_stems",
    "list_scope_stems",
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

    Examples
    --------
    >>> from liwca.datasets import dictionaries
    >>> dictionaries.path("sleep")  # doctest: +SKIP
    PosixPath('.../dictionaries/sleep.dicx')
    >>> dictionaries.path("bigtwo", version="b")  # doctest: +SKIP
    PosixPath('.../dictionaries/bigtwo-vb.dicx')
    >>> dictionaries.path("wrad")  # doctest: +SKIP
    PosixPath('.../dictionaries/wrad.dicx')
    """
    # Resolve in priority order: curated public fetchers > translated stems >
    # user-made stems. Several names (e.g. "sleep", "honor", "mystical",
    # "threat") collide between the public set and the user-made set; the
    # public (curated) version wins.
    fetcher = globals().get(f"fetch_{name}")
    if fetcher is not None:
        fetcher(**kwargs)  # populate the cache
        if name == "bigtwo":
            cache_name = f"bigtwo-v{kwargs.get('version', 'a')}.dicx"
        elif name == "hedonometer":
            cache_name = f"hedonometer-{kwargs['language']}"
            if kwargs.get("version", "2") is not None:
                cache_name += f"-v{kwargs['version']}"
            cache_name += ".dicx"
        elif name == "scope":
            cache_name = f"scope-{kwargs['stem'].lower()}.dicx"
        elif name == "psychnorms":
            cache_name = f"psychnorms-{kwargs['stem'].lower()}.dicx"
        else:
            cache_name = f"{name}.dicx"
        return Path(_pup.path) / cache_name
    if name in _TRANSLATED_DICTIONARIES:
        _fetch_translated(name)
        return Path(_pup.path) / f"{name}.dicx"
    if name in _USERMADE_DICTIONARIES:
        _fetch_usermade(name)
        return _usermade_dicx_path(name)
    available = sorted(n.removeprefix("fetch_") for n in __all__ if n.startswith("fetch_"))
    raise ValueError(f"Unknown dictionary {name!r}; available: {available}")


# ---------------------------------------------------------------------------
# Pooch processor: parse a source file once, cache as .dicx
# ---------------------------------------------------------------------------


class BuildDicx:
    """Pooch processor that parses a source dictionary file and caches as ``.dicx``.

    Sibling of :class:`liwca.datasets._common.CacheCsv` for the dictionaries
    module. On first run (``action`` is ``"download"`` or ``"update"``),
    ``build_fn`` is called on the downloaded source file and the resulting
    DataFrame is written as ``cache_name`` next to the source - via
    :func:`liwca.io.write_dicx` for binary dictionaries (default) or
    :func:`liwca.io.write_dicx_weighted` when ``weighted=True``. On
    subsequent runs (``action == "fetch"`` and the .dicx exists), the
    cached path is returned directly with no parsing or rewriting.

    Parameters
    ----------
    build_fn : callable
        Receives the downloaded source file as a :class:`~pathlib.Path` and
        returns a dictionary :class:`~pandas.DataFrame` (lowercase string
        index named ``"DicTerm"``, columns named ``"Category"``). Cells
        must be int8 0/1 when ``weighted=False``, or float64 when
        ``weighted=True``.
    cache_name : str
        Filename for the cached .dicx; written alongside the source file.
    weighted : bool, default ``False``
        If ``False`` (default), the output is validated and written as a
        binary ``.dicx`` (``X``/empty cells). If ``True``, it is written
        as a weighted ``.dicx`` with numeric cells (signed allowed).
    """

    def __init__(
        self,
        build_fn: Callable[[Path], pd.DataFrame],
        cache_name: str,
        *,
        weighted: bool = False,
    ) -> None:
        self.build_fn = build_fn
        self.cache_name = cache_name
        self.weighted = weighted

    def __call__(self, fname: str, action: str, pup: pooch.Pooch) -> str:
        cache_path = Path(fname).parent / self.cache_name
        if action == "fetch" and cache_path.exists():
            return str(cache_path)
        df = self.build_fn(Path(fname))
        if self.weighted:
            write_dicx_weighted(df, cache_path)
        else:
            write_dicx(df, cache_path)
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
        f"bigtwo-v{version}.dic",
        processor=BuildDicx(read_dic, f"bigtwo-v{version}.dicx"),
    )
    return read_dicx(dicx_path)


def fetch_emfd() -> pd.DataFrame:
    """
    Fetch the extended moral foundations 2.0 dictionary.

    See the `Moral Foundations Dictionary 2.0 OSF page <https://osf.io/ezn37>`__.
    """
    dicx_path = _pup.fetch("emfd.dic", processor=BuildDicx(read_dic, "emfd.dicx"))
    return read_dicx(dicx_path)


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
    return read_dicx(dicx_path)


def fetch_hedonometer(language: str = "en", version: str | None = "2") -> pd.DataFrame:
    """
    Fetch the Hedonometer dictionary.

    See the Hedonometer website `words <https://hedonometer.org/words/>`__
    and `API <https://hedonometer.org/api.html>`__ pages for more details,
    including available languages, versions, and direct download links.

    If used, cite:
    Alshaabi et al., 2021, *Plos One*,
    How the world's collective attention is being paid to a pandemic:
    COVID-19 related n-gram time series for 24 languages on Twitter
    doi:`10.1371/journal.pone.0244476 <https://doi.org/10.1371/journal.pone.0244476>`__

    Dodds et al., 2015, *PNAS*,
    Human language reveals a universal positivity bias
    doi:`10.1073/pnas.1411678112 <https://doi.org/10.1073/pnas.1411678112>`__

    Kloumann et al., 2012, *PloS One*,
    Positivity of the English language
    doi:`10.1371/journal.pone.0029484 <https://doi.org/10.1371/journal.pone.0029484>`__

    .. warning::
        Non-English files (``de``, ``es``, etc.) may contain both capitalized
        and lowercase variants of the same word. This function lowercases all
        terms and averages labMT scores across case-variants to satisfy the
        unique lowercase ``DicTerm`` index requirement. The result may have
        fewer rows than the raw JSON, with averaged scores.

    Notes
    -----
    Language ``id`` does not have a version 2 on the site, but it exists.
    Language ``zh`` does not have a version 1 on the site, but it exists.
    Language ``uk-ru`` does not have a version specification.
    """
    _HEDONOMETER_LANGUAGES = {"ar", "de", "en", "es", "fr", "id", "ko", "pt", "ru", "uk-ru", "zh"}
    _HEDONOMETER_VERSIONS = {"1", "2", None}
    assert language in _HEDONOMETER_LANGUAGES, f"language must be one of {_HEDONOMETER_LANGUAGES}"
    assert version in _HEDONOMETER_VERSIONS, f"version must be one of {_HEDONOMETER_VERSIONS}"
    if language == "uk-ru":
        assert version is None, "language 'uk-ru' does not have a version specification"
    registry_stem = f"hedonometer-{language}"
    if version is not None:
        registry_stem += f"-v{version}"
    registry_name = f"{registry_stem}.json"
    dicx_name = f"{registry_stem}.dicx"

    def _build(source_path: Path) -> pd.DataFrame:
        with source_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame.from_records(data["objects"], columns=["happs", "word"], index="word")
        df = df.astype("float64")
        # Some non-English Hedonometer files (e.g. German, Spanish) ship both
        # capitalized and lowercase variants of the same word as distinct
        # entries (e.g. "Ähnlich" + "ähnlich"). Lowercase here and average
        # the labMT scores across case-variants so the (lowercase-only,
        # unique) schema validates.
        df.index = df.index.str.lower()
        df = df.groupby(level=0).mean().sort_index()
        return df.rename_axis("DicTerm").rename(columns={"happs": "labMT"})

    dicx_path = _pup.fetch(
        registry_name,
        processor=BuildDicx(_build, dicx_name, weighted=True),
    )
    return read_dicx_weighted(dicx_path)


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
    dicx_path = _pup.fetch("honor.dic", processor=BuildDicx(read_dic, "honor.dicx"))
    return read_dicx(dicx_path)


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
    return read_dicx(dicx_path)


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
    return read_dicx(dicx_path)


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
    return read_dicx(dicx_path)


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
    return read_dicx(dicx_path)


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

    def _build(source_path: Path) -> pd.DataFrame:
        df = pd.read_csv(
            source_path,
            sep=" ",
            skiprows=11,
            names=["DicTerm", "ReferentialActivity"],
            index_col="DicTerm",
        ).astype("float64")
        return df.rename_axis("DicTerm").rename_axis("Category", axis=1)

    dicx_path = _pup.fetch(
        "wrad.Wt",
        processor=BuildDicx(_build, "wrad.dicx", weighted=True),
    )
    return read_dicx_weighted(dicx_path)


# ---------------------------------------------------------------------------
# Metabase fetchers: SCOPE and psychNorms
# ---------------------------------------------------------------------------
#
# SCOPE and psychNorms are *metabases* - large tables where most columns are
# individual published lexicons (concreteness, valence, arousal, etc.) with
# float-valued scores per word. ``fetch_scope(stem)`` and
# ``fetch_psychnorms(stem)`` slice one column out of the metabase, lower-case
# the word index (averaging case-variants when the source ships both), and
# cache the result as a single-category weighted ``.dicx`` per stem. The full
# metabase is downloaded once; each fresh stem pays a one-time parse cost.
#
# The metadata file/sheet that ships with each source classifies columns
# (e.g. SCOPE Level.1 = "Response Variables" marks behavioural RTs, not
# lexicons; psychNorms ``category == 'part_of_speech'`` marks POS tags).
# Lexicon-vs-non-lexicon stems are derived from those classifications and
# cross-checked against actual data dtypes; the result is memoised.


_SCOPE_STEMS_CACHE: dict[str, str] | None = None
_PSYCHNORMS_STEMS_CACHE: frozenset[str] | None = None


def _scope_stems() -> dict[str, str]:
    """Return a mapping of lowercase stem -> canonical SCOPE column name."""
    global _SCOPE_STEMS_CACHE
    if _SCOPE_STEMS_CACHE is not None:
        return _SCOPE_STEMS_CACHE
    source_path = Path(_pup.fetch("scope.xlsx"))
    meta = pd.read_excel(source_path, sheet_name="metadata")
    # Drop behavioural Response Variables (RT/accuracy of lexical decision,
    # naming, etc.) - they are measurements, not lexicons.
    meta = meta[meta["Level.1"] != "Response Variables"]
    candidate_names = meta["Name"].dropna().astype(str).tolist()
    # Cross-check against actual data dtypes: drop non-numeric columns
    # (POS tags, IPA strings, comma-separated semantic vectors, etc.).
    sample = pd.read_excel(
        source_path,
        sheet_name="data",
        usecols=lambda c: c in candidate_names,
        nrows=200,
    )
    numeric_cols = sample.select_dtypes(include="number").columns
    mapping = {c.lower(): c for c in candidate_names if c in numeric_cols}
    if len(mapping) != len(set(mapping)):
        raise ValueError("SCOPE column names collide under lowercase normalisation")
    _SCOPE_STEMS_CACHE = mapping
    return _SCOPE_STEMS_CACHE


def _psychnorms_stems() -> frozenset[str]:
    """Return the set of valid psychNorms stems (already lowercase snake_case)."""
    global _PSYCHNORMS_STEMS_CACHE
    if _PSYCHNORMS_STEMS_CACHE is not None:
        return _PSYCHNORMS_STEMS_CACHE
    meta_path = Path(_pup.fetch("psychnorms-metadata.csv"))
    meta = pd.read_csv(meta_path)
    # Drop part-of-speech tag columns - they are categorical strings, not
    # lexicons. All other psychNorms norms are float-valued.
    lexicons = meta.loc[meta["category"] != "part_of_speech", "norm"]
    _PSYCHNORMS_STEMS_CACHE = frozenset(lexicons.dropna().astype(str))
    return _PSYCHNORMS_STEMS_CACHE


def _resolve_scope_stem(stem: str) -> str:
    """Lowercase a SCOPE stem and resolve it to the canonical column name."""
    stems = _scope_stems()
    canonical = stems.get(stem.lower())
    if canonical is None:
        raise ValueError(
            f"Unknown SCOPE stem {stem!r}; "
            f"see liwca.datasets.dictionaries.list_scope_stems() for valid names."
        )
    return canonical


def _resolve_psychnorms_stem(stem: str) -> str:
    """Validate a psychNorms stem and return it unchanged (already canonical)."""
    stem_lc = stem.lower()
    if stem_lc not in _psychnorms_stems():
        raise ValueError(
            f"Unknown psychNorms stem {stem!r}; "
            f"see liwca.datasets.dictionaries.list_psychnorms_stems() for valid names."
        )
    return stem_lc


def list_scope_stems() -> list[str]:
    """Return the sorted list of valid SCOPE stems for :func:`fetch_scope`.

    Stems are lowercase column names from the SCOPE ``data`` sheet. Behavioural
    Response Variables (lexical decision RT/accuracy, naming, etc.) and
    non-numeric columns (POS tags, IPA, distributed semantic vectors) are
    excluded. The first call downloads ``scope.xlsx`` if not already cached.

    Returns
    -------
    list of str
        Sorted lowercase stem names. Pass any of these to
        :func:`fetch_scope`.

    See Also
    --------
    liwca.datasets.tables.fetch_scope :
        Fetch the SCOPE column-classification metadata table for richer
        information about each stem (Level.1/Level.2 grouping, source,
        citation).
    """
    return sorted(_scope_stems())


def list_psychnorms_stems() -> list[str]:
    """Return the sorted list of valid psychNorms stems for :func:`fetch_psychnorms`.

    Stems are lowercase ``norm`` names from ``psychnorms-metadata.csv``,
    excluding the two part-of-speech tag columns (which are categorical
    strings rather than lexicons). The first call downloads
    ``psychnorms-metadata.csv`` if not already cached.

    Returns
    -------
    list of str
        Sorted lowercase stem names. Pass any of these to
        :func:`fetch_psychnorms`.

    See Also
    --------
    liwca.datasets.tables.fetch_psychnorms :
        Fetch the psychNorms column-classification metadata table for richer
        information about each stem (category, description, source, citation).
    """
    return sorted(_psychnorms_stems())


def fetch_scope(stem: str) -> pd.DataFrame:
    """Fetch one lexicon column from SCOPE as a weighted dictionary.

    The `South CarOlina Psycholinguistic metabase (SCOPE)
    <https://sc.edu/study/colleges_schools/artsandsciences/psychology/research_clinical_facilities/scope/>`__
    aggregates over 250 psycholinguistic variables for ~190,000 words and
    ~80,000 nonwords. This fetcher downloads ``scope.xlsx`` once and slices
    the requested column into a single-category weighted ``.dicx`` cached
    alongside the source file.

    Word case-variants in the source (e.g. ``Café`` vs ``café``) are merged
    by averaging their scores so the lowercase ``DicTerm`` index is unique.

    Parameters
    ----------
    stem : str
        Name of the SCOPE column to extract (case-insensitive). For
        example, ``"concreteness_brysbaert"`` resolves to the canonical
        ``Concreteness_Brysbaert`` column. See :func:`list_scope_stems`
        for valid names, or :func:`liwca.datasets.tables.fetch_scope` for
        the classification metadata.

    Returns
    -------
    :class:`pandas.DataFrame`
        Weighted dictionary with one column named after the canonical SCOPE
        column and a lowercase ``DicTerm`` index.

    If used, cite:
    Gao et al., 2023. SCOPE: The South Carolina psycholinguistic metabase.
    *Behavior Research Methods*
    doi:`10.3758/s13428-022-01934-0 <https://doi.org/10.3758/s13428-022-01934-0>`__

    Examples
    --------
    >>> from liwca.datasets import dictionaries
    >>> dx = dictionaries.fetch_scope("concreteness_brysbaert")  # doctest: +SKIP
    """
    canonical = _resolve_scope_stem(stem)
    cache_name = f"scope-{stem.lower()}.dicx"

    def _build(source_path: Path) -> pd.DataFrame:
        df = pd.read_excel(
            source_path,
            sheet_name="data",
            usecols=["Word", canonical],
        )
        df = df.dropna(subset=[canonical])
        df["Word"] = df["Word"].astype(str).str.lower()
        # Average case-variants so the (unique, lowercase) DicTerm index validates.
        df = df.groupby("Word", as_index=True)[[canonical]].mean().sort_index()
        return df.astype("float64").rename_axis("DicTerm", axis=0).rename_axis("Category", axis=1)

    dicx_path = _pup.fetch(
        "scope.xlsx",
        processor=BuildDicx(_build, cache_name, weighted=True),
    )
    return read_dicx_weighted(dicx_path)


def fetch_psychnorms(stem: str) -> pd.DataFrame:
    """Fetch one lexicon column from psychNorms as a weighted dictionary.

    The `psychNorms metabase <https://github.com/Zak-Hussain/psychNorms>`__
    aggregates 290+ psycholinguistic norms for ~107,000 words across 27
    semantic categories (frequency, valence, arousal, concreteness, sensory
    ratings, etc.). This fetcher downloads ``psychnorms.zip`` once and slices
    the requested column into a single-category weighted ``.dicx`` cached at
    the dictionaries cache root.

    Parameters
    ----------
    stem : str
        Name of the psychNorms ``norm`` to extract (case-insensitive).
        psychNorms columns are already lowercase ``snake_case``, so the stem
        usually matches the column name verbatim (e.g.
        ``"concreteness_brysbaert"``). See :func:`list_psychnorms_stems`
        for valid names, or :func:`liwca.datasets.tables.fetch_psychnorms`
        for the classification metadata.

    Returns
    -------
    :class:`pandas.DataFrame`
        Weighted dictionary with one column named after the psychNorms norm
        and a lowercase ``DicTerm`` index.

    If used, cite:
    Hussain et al., 2024.
    Probing the contents of semantic representations from text, behavior, and
    brain data using the psychNorms metabase. *arXiv*
    doi:`10.48550/arXiv.2412.04936 <https://doi.org/10.48550/arXiv.2412.04936>`__

    Examples
    --------
    >>> from liwca.datasets import dictionaries
    >>> dx = dictionaries.fetch_psychnorms("concreteness_brysbaert")  # doctest: +SKIP
    """
    canonical = _resolve_psychnorms_stem(stem)
    cache_path = Path(_pup.path) / f"psychnorms-{canonical}.dicx"
    if not cache_path.exists():
        unzipped = _pup.fetch("psychnorms.zip", processor=pooch.Unzip())
        csv_path = next(Path(f) for f in unzipped if Path(f).name == "psychNorms.csv")
        df = pd.read_csv(csv_path, usecols=["word", canonical], low_memory=False)
        df = df.dropna(subset=[canonical])
        df["word"] = df["word"].astype(str).str.lower()
        df = df.groupby("word", as_index=True)[[canonical]].mean().sort_index()
        df = df.astype("float64").rename_axis("DicTerm", axis=0).rename_axis("Category", axis=1)
        write_dicx_weighted(df, cache_path)
    return read_dicx_weighted(cache_path)


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
    return read_dicx(dicx_path)


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
    return read_dicx(dicx_path)


_TRANSLATED_DICTIONARIES = frozenset(
    {
        "LIWC2001-German",
        "LIWC2001-Spanish",
        "LIWC2007-Brazilian-Portuguese",
        "LIWC2007-Chinese-Simplified",
        "LIWC2007-Chinese-Traditional",
        "LIWC2007-Dutch",
        "LIWC2007-French",
        "LIWC2007-Italian",
        "LIWC2007-Norwegian",
        "LIWC2007-Russian",
        "LIWC2007-Serbian",
        "LIWC2007-Spanish",
        "LIWC2015-Brazilian-Portuguese",
        "LIWC2015-Chinese-Simplified-v1.5",
        "LIWC2015-Chinese-Simplified",
        "LIWC2015-Chinese-Traditional-v1.5",
        "LIWC2015-Chinese-Traditional",
        "LIWC2015-Dutch",
        "LIWC2015-Japanese",
        "LIWC2015-Marathi",
        "LIWC2015-Romanian",
        "LIWC2015-Ukrainian",
    }
)


def _normalize_translated_dicx(raw_path: Path, normalized_path: Path) -> None:
    """Rewrite an old-format translated .dicx as a strict-format .dicx.

    Some translated dictionaries from LIWC use the older ``Entry`` term-column
    header instead of ``DicTerm``, and ``1``/empty for binary membership
    instead of ``X``/empty. This function normalizes both into the LIWC-22
    ``DicTerm`` + ``X``/empty format so downstream readers can stay strict.
    """
    df = pd.read_csv(raw_path, dtype="string", keep_default_na=False)
    # Header normalisation: rename whatever the term column is called to "DicTerm".
    first_col = df.columns[0]
    if first_col != "DicTerm":
        df = df.rename(columns={first_col: "DicTerm"})
    df = df.set_index("DicTerm")
    # Cell normalisation: any "1" becomes "X"; everything else (including "X"
    # and empty) is preserved.
    df = df.where(df != "1", "X")
    df.to_csv(normalized_path, index=True, lineterminator="\n", encoding="utf-8")


def _fetch_translated(fstem: str) -> pd.DataFrame:
    """
    Fetch a translated dictionary shared on the LIWC site.

    Dictionaries are available on the
    `LIWC dictionaries page <https://www.liwc.app/dictionaries>`__.

    Some files use the older ``Entry`` header and ``1``/empty cell convention;
    these are normalized to the standard ``DicTerm`` + ``X``/empty format and
    cached alongside the source archive so subsequent calls (and the
    :func:`path` resolver) hit a strict, LIWC-22-compatible ``.dicx``.

    .. note:: These dictionaries require login for access.
    """
    if fstem not in _TRANSLATED_DICTIONARIES:
        raise ValueError(f"Unknown translated dictionary {fstem!r}")
    downloader = AuthorizedZenodoDownloader()
    processor = pooch.Unzip()
    fnames = _pup.fetch("translated.zip", downloader=downloader, processor=processor)
    fpaths = {Path(fn).name: Path(fn) for fn in fnames}
    raw_path = fpaths[f"{fstem}.dicx"]
    normalized_path = Path(_pup.path) / f"{fstem}.dicx"
    if not normalized_path.exists():
        _normalize_translated_dicx(raw_path, normalized_path)
    return read_dicx(normalized_path)


_USERMADE_DICTIONARIES = frozenset(
    {
        "absolutist",
        "age-stereotypes",
        "agitation-dejection",
        "ai-focus",
        "american-indian-stereotype",
        "anticoagulation",
        "behavioral-activation",
        "big-two-agency-communion",
        "body-type",
        "brand-personality",
        "bureaucratic",
        "climate-change",
        "color-russian",
        "color",
        "controversial",
        "corporate-social-responsibility",
        "cost-benefit",
        "creativity-and-innovation",
        "crovitz-innovator-identification-method",
        "dehumanization",
        "diccionario-de-polaridad-y-clase-de-palabras-esp",
        "digital-orientation-dimensions",
        "emolex",
        "empath-default",
        "empathic-concern",
        "english-personal-values-self-direction",
        "english-prime",
        "enriched-american-food",
        "entrepreneurial-and-mentoring",
        "extended-moral-foundations",
        "foresight",
        "forest-values",
        "general-inquirer-iv",
        "global-citizen",
        "grant-evaluation",
        "grievance",
        "handmade-production-cue",
        "home-perceptions",
        "honor",
        "imagination",
        "incel-violent-extremism",
        "invective",
        "irish-far-right-mobilisation",
        "linguistic-category-model",
        "loughran-mcdonald-financial-sentiment-2018",
        "loughran-mcdonald-financial-sentiment",
        "loughran-mcdonald",
        "marcadoresdiscursivos-espanol",
        "masculine-feminine",
        "mind-perception",
        "mindfulness",
        "moral-foundations-2.0",
        "moral-foundations",
        "moral-justification",
        "moral-universalism-french",
        "moral-universalism-german",
        "moral-universalism-italian",
        "moral-universalism-spanish",
        "morality-as-cooperation",
        "motivated-social-cognition",
        "mystical",
        "nonconformity",
        "nostalgia",
        "open-science",
        "pain",
        "personal-values",
        "physiological-sensations",
        "policy-position-uk",
        "policy-position",
        "pornography",
        "portuguese-slang",
        "privacy",
        "promotion",
        "prorefugee-content",
        "prosocial",
        "qualia",
        "regressive-imagery",
        "regulatory-mode",
        "restless-ceos",
        "romantic-love",
        "security",
        "self-care",
        "self-determination-self-talk",
        "self-transcendent-emotion",
        "situational-8",
        "sleep",
        "social-ties",
        "stem-german",
        "stereotype-content",
        "stress",
        "threat",
        "transactive-memory-systems-strength",
        "urban-dictionary",
        "violence-against-women",
        "water-metaphor",
        "weighted-referential-activity",
        "weighted-reflection-reorganizing-list",
        "well-being",
        "whirlall",
    }
)

# Subset of _USERMADE_DICTIONARIES whose .dicx contains numeric weights instead
# of binary `X`/empty cells. Routed through read_dicx_weighted.
_WEIGHTED_USERMADE_DICTIONARIES = frozenset(
    {
        "enriched-american-food",
        "extended-moral-foundations",
        "loughran-mcdonald",
        "stereotype-content",
        "weighted-referential-activity",
        "weighted-reflection-reorganizing-list",
    }
)


def _usermade_dicx_path(fstem: str) -> Path:
    """Return the on-disk path to a usermade .dicx, fetching/unzipping if needed.

    Used by both :func:`_fetch_usermade` and :func:`path` so they share the
    same cache-materialisation logic.
    """
    fnames = _pup.fetch(
        "usermade.zip",
        downloader=AuthorizedZenodoDownloader(),
        processor=pooch.Unzip(),
    )
    fpaths = {Path(fn).name: Path(fn) for fn in fnames}
    return fpaths[f"{fstem}.dicx"]


def _fetch_usermade(fstem: str) -> pd.DataFrame:
    """
    Fetch a user-made dictionary shared on the LIWC site.

    Dictionaries are available on the
    `LIWC dictionaries page <https://www.liwc.app/dictionaries>`__.

    Most user-made files use the binary ``X``/empty cell convention; a small
    set listed in :data:`_WEIGHTED_USERMADE_DICTIONARIES` ship numeric weights
    and are routed through :func:`liwca.io.read_dicx_weighted`.

    .. note:: These dictionaries require login for access.
    """
    if fstem not in _USERMADE_DICTIONARIES:
        raise ValueError(f"Unknown user-made dictionary {fstem!r}")
    fpath = _usermade_dicx_path(fstem)
    if fstem in _WEIGHTED_USERMADE_DICTIONARIES:
        return read_dicx_weighted(fpath)
    return read_dicx(fpath)
