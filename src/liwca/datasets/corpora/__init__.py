"""Remote text corpora - per-corpus fetch functions.

Each function downloads its corpus to a local cache (if not already
present) and returns a :class:`pathlib.Path` to the downloaded file.
The cache location defaults to
``pooch.os_cache("liwca") / "corpora"`` and can be overridden by
setting the ``LIWCA_DATA_DIR`` environment variable - corpora are
then cached in ``$LIWCA_DATA_DIR/corpora/``.

Power users who want the raw local file path can call
``liwca.datasets.corpora._pup.fetch(filename)`` directly.
"""

from __future__ import annotations

import logging
import os
from importlib.resources import files as _files
from pathlib import Path

import pooch

__all__ = [
    "fetch_hippocorpus",
    "fetch_liwc_demo_data",
]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pooch download registry
# ---------------------------------------------------------------------------

_root = Path(os.environ.get("LIWCA_DATA_DIR") or pooch.os_cache("liwca"))
_pup = pooch.create(path=_root / "corpora", base_url="")
with open(str(_files("liwca.datasets.corpora").joinpath("registry.txt"))) as _f:
    _pup.load_registry(_f)


# ---------------------------------------------------------------------------
# Fetch functions
# ---------------------------------------------------------------------------


def fetch_hippocorpus() -> Path:
    """
    Fetch the Hippocorpus dataset of imagined, recalled, and retold stories.

    A crowdsourced corpus of short English narratives in which the same
    events appear as both lived experiences (recalled, retold) and
    imagined fictions, released by Microsoft Research.

    Returns
    -------
    :class:`pathlib.Path`
        Local path to the downloaded ``hippocorpus-u20220112.zip`` file.
        The archive is not extracted - use :mod:`zipfile` or your
        preferred tool to read entries.

    Notes
    -----
    Described in Sap et al.\\ [1]_ and distributed via the Microsoft
    download CDN\\ [2]_.

    References
    ----------
    .. [1] TBD
    .. [2] `https://download.microsoft.com/download/3/c/3/3c388755-ac68-4858-8343-9acfb33c631d/hippocorpus-u20220112.zip
           <https://download.microsoft.com/download/3/c/3/3c388755-ac68-4858-8343-9acfb33c631d/hippocorpus-u20220112.zip>`__

    Examples
    --------
    >>> from liwca.datasets import corpora
    >>> path = corpora.fetch_hippocorpus()  # doctest: +SKIP
    """
    return Path(_pup.fetch("hippocorpus-u20220112.zip"))


def fetch_liwc_demo_data() -> Path:
    """
    Fetch the LIWC-22 demo data archive.

    A zip of example input/output files distributed with the LIWC-22
    application. Useful for trying analysis pipelines without having
    to bring your own texts.

    Returns
    -------
    :class:`pathlib.Path`
        Local path to the downloaded ``liwc-22-demo-data.zip`` file.
        The archive is not extracted - use :mod:`zipfile` or your
        preferred tool to read entries.

    Notes
    -----
    Distributed on the LIWC website\\ [1]_.

    References
    ----------
    .. [1] `https://www.liwc.app/static/files/liwc-22-demo-data.zip
           <https://www.liwc.app/static/files/liwc-22-demo-data.zip>`__

    Examples
    --------
    >>> from liwca.datasets import corpora
    >>> path = corpora.fetch_liwc_demo_data()  # doctest: +SKIP
    """
    return Path(_pup.fetch("liwc-22-demo-data.zip"))
