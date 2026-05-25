"""Tests for liwca top-level package helpers (set_log_level)."""

from __future__ import annotations

import logging

import liwca


def _strip_real_handlers() -> list[logging.Handler]:
    """Remove non-Null handlers from the package logger and return the originals.

    Lets each test start with a clean ``"liwca"`` logger so other tests'
    handlers (and any earlier ``set_log_level`` calls in this run) don't
    interfere with assertions about handler counts.
    """
    pkg_logger = logging.getLogger("liwca")
    originals = list(pkg_logger.handlers)
    pkg_logger.handlers = [h for h in originals if isinstance(h, logging.NullHandler)]
    return originals


def _restore_handlers(handlers: list[logging.Handler]) -> None:
    pkg_logger = logging.getLogger("liwca")
    pkg_logger.handlers = handlers


class TestSetLogLevel:
    """liwca.set_log_level installs a StreamHandler exactly once."""

    def test_adds_stream_handler(self) -> None:
        originals = _strip_real_handlers()
        try:
            liwca.set_log_level("DEBUG")
            pkg_logger = logging.getLogger("liwca")
            stream_handlers = [
                h
                for h in pkg_logger.handlers
                if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.NullHandler)
            ]
            assert len(stream_handlers) == 1
            assert pkg_logger.level == logging.DEBUG
        finally:
            _restore_handlers(originals)

    def test_repeated_calls_do_not_duplicate_handlers(self) -> None:
        originals = _strip_real_handlers()
        try:
            liwca.set_log_level("INFO")
            liwca.set_log_level("WARNING")
            liwca.set_log_level(logging.ERROR)
            pkg_logger = logging.getLogger("liwca")
            stream_handlers = [
                h
                for h in pkg_logger.handlers
                if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.NullHandler)
            ]
            assert len(stream_handlers) == 1
            assert pkg_logger.level == logging.ERROR
        finally:
            _restore_handlers(originals)

    def test_default_level_is_info(self) -> None:
        originals = _strip_real_handlers()
        try:
            liwca.set_log_level()
            assert logging.getLogger("liwca").level == logging.INFO
        finally:
            _restore_handlers(originals)
