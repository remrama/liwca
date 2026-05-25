"""liwca.datasets - fetchers and the shared extension API.

The helpers re-exported here (``make_pup``, ``UnzipToCsv``, ``CacheCsv``,
``BuildDicx``, ``get_location``) are the supported surface for third-party
packages that add their own fetchers on top of liwca. Point ``make_pup``'s
``registry_package`` kwarg at your own resource package and the cache layout
is shared with liwca's built-in fetchers.
"""

from liwca.datasets._common import (
    BuildDicx,
    CacheCsv,
    UnzipToCsv,
    get_location,
    make_pup,
)

__all__ = [
    "BuildDicx",
    "CacheCsv",
    "UnzipToCsv",
    "get_location",
    "make_pup",
]
