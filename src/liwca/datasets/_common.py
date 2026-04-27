"""Shared helpers for the dataset submodules.

Provides a Pooch factory (one cache subdirectory per category, all sharing
the same ``data/registry.txt``), a Zenodo-authenticated downloader for
restricted-access fetchers, and a Pooch processor that unzips an archive
and caches a parsed DataFrame as CSV alongside it.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from importlib.resources import files
from pathlib import Path

import pandas as pd
import pooch

__all__ = ["UnzipToCsv", "authorized_zenodo_downloader", "get_location", "make_pup"]


def get_location(pup: pooch.Pooch) -> Path:
    """Return the local cache directory used by ``pup``.

    The directory may not exist yet if no files have been fetched.
    """
    return Path(pup.path)


def make_pup(category: str) -> pooch.Pooch:
    """Build a :class:`pooch.Pooch` for one dataset category.

    Each category (``"corpora"``, ``"dictionaries"``, ``"tables"``) gets its
    own cache subdirectory under ``$LIWCA_DATA_DIR`` (or the OS user cache),
    but all categories load the same shared registry file at
    ``liwca/datasets/data/registry.txt``.
    """
    root = Path(os.environ.get("LIWCA_DATA_DIR") or pooch.os_cache("liwca"))
    pup = pooch.create(path=root / category, base_url="")
    with open(str(files("liwca.datasets.data").joinpath("registry.txt"))) as f:
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


def authorized_zenodo_downloader(**kwargs) -> pooch.HTTPDownloader:
    """Build a Pooch HTTP downloader carrying a Zenodo bearer token.

    Reads ``ZENODO_TOKEN`` from the environment and attaches it as an
    ``Authorization: Bearer <token>`` header on every request, so restricted
    Zenodo records can be fetched.

    Raises
    ------
    OSError
        If ``ZENODO_TOKEN`` is unset.
    """
    if (token := os.environ.get("ZENODO_TOKEN")) is None:
        raise OSError("A `ZENODO_TOKEN` with repository access must be set to fetch this file.")
    authorization = f"Bearer {token}"
    return pooch.HTTPDownloader(headers={"Authorization": authorization}, **kwargs)
