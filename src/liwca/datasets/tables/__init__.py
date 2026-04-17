"""Remote published tables (norms, descriptive statistics, etc.) - per-table fetch functions.

Each function downloads its table to a local cache (if not already
present) and returns a :class:`pathlib.Path` to the downloaded file.
The cache location defaults to
``pooch.os_cache("liwca") / "tables"`` and can be overridden by
setting the ``LIWCA_DATA_DIR`` environment variable - tables are
then cached in ``$LIWCA_DATA_DIR/tables/``.

Power users who want the raw local file path can call
``liwca.datasets.tables._pup.fetch(filename)`` directly.
"""

from __future__ import annotations

import logging
import os
from importlib.resources import files as _files
from pathlib import Path

import pooch

__all__ = [
    "fetch_liwc22norms",
    "fetch_liwc2015norms",
]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pooch download registry
# ---------------------------------------------------------------------------

_root = Path(os.environ.get("LIWCA_DATA_DIR") or pooch.os_cache("liwca"))
_pup = pooch.create(path=_root / "tables", base_url="")
with open(str(_files("liwca.datasets.tables").joinpath("registry.txt"))) as _f:
    _pup.load_registry(_f)


# ---------------------------------------------------------------------------
# Fetch functions
# ---------------------------------------------------------------------------


def fetch_liwc22norms() -> Path:
    """
    Fetch the LIWC-22 descriptive statistics ("Test Kitchen" norms) table.

    Reference means and standard deviations for every LIWC-22 category
    across the corpora in the "Test Kitchen" reference set.

    Returns
    -------
    :class:`pathlib.Path`
        Local path to the downloaded
        ``LIWC-22.Descriptive.Statistics-Test.Kitchen.xlsx`` file.

    Notes
    -----
    Distributed on the LIWC website\\ [1]_.

    References
    ----------
    .. [1] TBD

    Examples
    --------
    >>> from liwca.datasets import tables
    >>> path = tables.fetch_liwc22norms()  # doctest: +SKIP
    """
    return Path(_pup.fetch("LIWC-22.Descriptive.Statistics-Test.Kitchen.xlsx"))


def fetch_liwc2015norms() -> Path:
    """
    Fetch the LIWC-2015 descriptive statistics norms table.

    Reference means and standard deviations for every LIWC-2015 category
    across the reference corpora reported in the LIWC-2015 technical
    manual.

    Returns
    -------
    :class:`pathlib.Path`
        Local path to the downloaded
        ``LIWC2015.Descriptive.Statistics.Full.xlsx`` file.

    Notes
    -----
    Distributed on the LIWC website\\ [1]_.

    References
    ----------
    .. [1] TBD

    Examples
    --------
    >>> from liwca.datasets import tables
    >>> path = tables.fetch_liwc2015norms()  # doctest: +SKIP
    """
    return Path(_pup.fetch("LIWC2015.Descriptive.Statistics.Full.xlsx"))
