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

import pandas as pd
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


def _authorized_zenodo_downloader(**kwargs) -> pooch.HTTPDownloader:
    if (token := os.environ.get("ZENODO_TOKEN")) is None:
        raise OSError("A `ZENODO_TOKEN` with repository access must be set to fetch this file.")
    authorization = f"Bearer {token}"
    downloader = pooch.HTTPDownloader(headers={"Authorization": authorization}, **kwargs)
    return downloader


# ---------------------------------------------------------------------------
# Fetch functions
# ---------------------------------------------------------------------------


def fetch_hippocorpus() -> pd.DataFrame:
    """
    Fetch the Hippocorpus dataset of imagined, recalled, and retold stories.

    A crowdsourced corpus of short English narratives in which the same
    events appear as both lived experiences (recalled, retold) and
    imagined fictions, released by Microsoft Research.

    Returns
    -------
    :class:`pandas.DataFrame`
        :class:`~pandas.DataFrame` of the ``hcV3-stories.csv`` file.

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
    processor = pooch.Unzip(
        members=[
            "hcV3-eventAnnots.csv",
            "hcv3-eventAnnotsAggOverWorkers.csv",
            "hcV3-stories.csv",
            "hippoCorpusV2.csv",
            "LinktoStudyTemplates.txt",
            "V2README.txt",
            "V3README.txt",
        ]
    )
    fnames = _pup.fetch("hippocorpus-u20220112.zip", processor=processor)
    fpaths = {Path(fn).name: Path(fn) for fn in fnames}
    fpath = fpaths["hcV3-stories.csv"]
    df = pd.read_csv(fpath)
    return df


def fetch_liwc_demo_data() -> Path:
    """
    Fetch the LIWC-22 demo data archive.

    A zip of example input/output files distributed with the LIWC-22
    application. Useful for trying analysis pipelines without having
    to bring your own texts.

    Returns
    -------
    :class:`pandas.DataFrame`
        :class:`~pandas.DataFrame` of all the individual ``.txt`` files from unzipped file.

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
    fnames = _pup.fetch("liwc-22-demo-data.zip", processor=pooch.Unzip())
    fpaths = {Path(fn).name: Path(fn) for fn in fnames}
    data = {}
    for k, v in fpaths.items():
        if k not in {"LICENSE.txt", "README.txt"}:
            data[v.stem] = v.read_text()
    ser = pd.Series(data, name="text").rename_axis("text_id")
    df = ser.to_frame()
    return df


def _fetch_testkitchen() -> pd.DataFrame:
    """
    Fetch the LIWC Test Kitchen corpus.

    .. note:: This is a restricted file that requires approved access.
    """
    downloader = _authorized_zenodo_downloader()
    processor = pooch.Unzip()
    fnames = _pup.fetch("testkitchen.zip", downloader=downloader, processor=processor)
    fpaths = {Path(fn).name: Path(fn) for fn in fnames}
    source_map = {}
    for fp in fpaths["AP_0001.txt"].parent.parent.glob("TK_*/*_0001.txt"):
        source_fullname = fp.parent.name.split("_", 1)[1]
        source_shortname = fp.stem.split("_")[0]
        source_map[source_shortname] = source_fullname
    data = {}
    # for fp in fpaths.values():
    for fp in list(fpaths.values())[:10]:
        data[fp.stem] = fp.read_text()
    ser = pd.Series(data, name="text").rename_axis("text_id")
    df = ser.to_frame()
    df.index = df.index.str.split("_").str[0].map(source_map)
    return df
