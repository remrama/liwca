"""Shared helpers for the dataset submodules and third-party extensions.

These helpers form the supported extension surface for packages that want to
add their own fetchers on top of liwca (e.g. ``liwca_private``):

- :func:`make_pup` — Pooch factory; one cache subdirectory per category,
  loading a registry file from any importable resource package.
- :class:`UnzipToCsv`, :class:`CacheCsv`, :class:`BuildDicx` — Pooch
  processors that parse a downloaded source once and cache the result
  (CSV or ``.dicx``) alongside it.

All are re-exported from :mod:`liwca.datasets` for convenience.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from importlib.resources import files
from pathlib import Path

import pandas as pd
import pooch

from ..io import write_dicx, write_dicx_weighted

__all__ = [
    "BuildDicx",
    "CacheCsv",
    "UnzipToCsv",
    "get_location",
    "make_pup",
]


def get_location(pup: pooch.Pooch) -> Path:
    """Return the local cache directory used by ``pup``.

    The directory may not exist yet if no files have been fetched.
    """
    return Path(pup.path)


def make_pup(
    category: str,
    *,
    registry_package: str = "liwca.datasets.data",
    registry_filename: str = "registry.txt",
) -> pooch.Pooch:
    """Build a :class:`pooch.Pooch` for one dataset category.

    Each category (``"corpora"``, ``"dictionaries"``, ``"tables"``) gets its
    own cache subdirectory under ``$LIWCA_DATA_DIR`` (or the OS user cache).
    By default, all categories load the same shared registry file at
    ``liwca/datasets/data/registry.txt``. Third-party packages can point
    ``registry_package`` / ``registry_filename`` at their own resource to
    extend liwca with private fetchers while sharing the cache layout.

    Parameters
    ----------
    category : str
        Cache subdirectory name (typically ``"corpora"``, ``"dictionaries"``,
        or ``"tables"``).
    registry_package : str, default ``"liwca.datasets.data"``
        Importable package containing the registry file, in
        :func:`importlib.resources.files` form.
    registry_filename : str, default ``"registry.txt"``
        Name of the registry file inside ``registry_package``.
    """
    root = Path(os.environ.get("LIWCA_DATA_DIR") or pooch.os_cache("liwca"))
    pup = pooch.create(path=root / category, base_url="")
    with open(str(files(registry_package).joinpath(registry_filename))) as f:
        pup.load_registry(f)
    return pup


class UnzipToCsv:
    """Pooch processor that unzips an archive, parses it, and caches as CSV.

    On first run (``action`` is ``"download"`` or ``"update"``), the archive
    is unzipped via :class:`pooch.Unzip`, the extracted member paths are
    handed to ``build_fn`` to construct a :class:`~pandas.DataFrame`, and
    the result is written as ``cache_name`` next to the source archive.
    On subsequent runs (``action == "fetch"`` and the CSV already exists),
    the cached path is returned directly with no parsing or unzipping.

    Returns the path (as ``str``) to the cached CSV; the caller is
    responsible for the ``pd.read_csv`` call (so each fetcher can pass
    its own ``index_col``, ``dtype``, etc.).

    Parameters
    ----------
    build_fn : callable
        Receives a list of unzipped member :class:`~pathlib.Path` objects
        and returns a :class:`~pandas.DataFrame`.
    cache_name : str
        Filename for the cached CSV; written alongside the source archive.
    members : list of str, optional
        Forwarded to :class:`pooch.Unzip` to restrict which archive members
        are extracted.
    """

    def __init__(
        self,
        build_fn: Callable[[list[Path]], pd.DataFrame],
        cache_name: str,
        *,
        members: list[str] | None = None,
    ) -> None:
        self.build_fn = build_fn
        self.cache_name = cache_name
        self.members = members

    def __call__(self, fname: str, action: str, pup: pooch.Pooch) -> str:
        cache_path = Path(fname).parent / self.cache_name
        if action == "fetch" and cache_path.exists():
            return str(cache_path)
        unzipper = pooch.Unzip(members=self.members)
        member_paths = unzipper(fname, action, pup)
        df = self.build_fn([Path(m) for m in member_paths])
        df.to_csv(cache_path)
        return str(cache_path)


class CacheCsv:
    """Pooch processor that parses a single source file and caches as CSV.

    Sibling of :class:`UnzipToCsv` for downloads that don't need unzipping.
    On first run (``action`` is ``"download"`` or ``"update"``), ``build_fn``
    is called on the downloaded file and the resulting DataFrame is written
    as ``cache_name`` next to the source. On subsequent runs
    (``action == "fetch"`` and the CSV exists), the cached path is returned
    directly with no parsing.

    Parameters
    ----------
    build_fn : callable
        Receives the downloaded source file as a :class:`~pathlib.Path` and
        returns a :class:`~pandas.DataFrame`.
    cache_name : str
        Filename for the cached CSV; written alongside the source file.
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
        df.to_csv(cache_path)
        return str(cache_path)


class BuildDicx:
    """Pooch processor that parses a source dictionary file and caches as ``.dicx``.

    Sibling of :class:`CacheCsv` for dictionary fetchers. On first run
    (``action`` is ``"download"`` or ``"update"``), ``build_fn`` is called on
    the downloaded source file and the resulting DataFrame is written as
    ``cache_name`` next to the source - via :func:`liwca.io.write_dicx` for
    binary dictionaries (default) or :func:`liwca.io.write_dicx_weighted`
    when ``weighted=True``. On subsequent runs (``action == "fetch"`` and
    the .dicx exists), the cached path is returned directly with no
    parsing or rewriting.

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
