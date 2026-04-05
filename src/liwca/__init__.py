import logging

from .count import *
from .io import *
from .liwc22 import *

__author__ = "Remington Mallett <mallett.remy@gmail.com>"
__version__ = "0.1.0"

# NullHandler prevents "No handlers could be found" warnings when liwca is
# imported as a library and the caller hasn't configured logging at all.
# On its own this produces no output — set_log_level() adds a real handler.
logging.getLogger(__name__).addHandler(logging.NullHandler())


def set_log_level(level: int | str = logging.INFO) -> None:
    """
    Configure logging output for the liwca package.

    Adds a :class:`~logging.StreamHandler` with a simple format to the
    ``"liwca"`` logger and sets the given level.  Safe to call multiple
    times — the handler is only added once.

    Parameters
    ----------
    level : int or str, optional
        Logging level (default ``logging.INFO``).
        Accepts constants like ``logging.DEBUG`` or strings like ``"DEBUG"``.

    Examples
    --------
    >>> import liwca
    >>> liwca.set_log_level("DEBUG")  # verbose output
    >>> liwca.set_log_level()  # INFO (default)
    """
    pkg_logger = logging.getLogger(__name__)
    # Avoid duplicate handlers on repeated calls.
    if not any(
        isinstance(h, logging.StreamHandler)
        for h in pkg_logger.handlers
        if not isinstance(h, logging.NullHandler)
    ):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(name)s | %(levelname)s | %(message)s"))
        pkg_logger.addHandler(handler)
    pkg_logger.setLevel(level)
