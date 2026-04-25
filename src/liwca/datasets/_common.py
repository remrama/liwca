"""Shared helpers for the dataset submodules.

Provides a Pooch factory (one cache subdirectory per category, all sharing
the same ``data/registry.txt``) and a Zenodo-authenticated downloader for
restricted-access fetchers.
"""

from __future__ import annotations

import os
from importlib.resources import files
from pathlib import Path

import pooch

__all__ = ["authorized_zenodo_downloader", "get_location", "make_pup"]


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
