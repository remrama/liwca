"""Tests for liwca.datasets._common shared helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pooch
import pytest

from liwca.datasets import corpora, dictionaries, tables
from liwca.datasets._common import AuthorizedZenodoDownloader

_GET_LOCATION_CASES = [
    ("corpora", corpora.get_location),
    ("dictionaries", dictionaries.get_location),
    ("tables", tables.get_location),
]


@pytest.mark.parametrize("category,get_location", _GET_LOCATION_CASES)
def test_get_location(category: str, get_location) -> None:
    """Per-module get_location() returns a Path ending in the category name."""
    loc = get_location()
    assert isinstance(loc, Path)
    assert loc.name == category


# ---------------------------------------------------------------------------
# AuthorizedZenodoDownloader: token check must be deferred until pooch
# actually needs to download (so cached fetches succeed without a token).
# ---------------------------------------------------------------------------


def test_authorized_zenodo_downloader_does_not_check_token_eagerly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Constructing the downloader with no ZENODO_TOKEN must not raise."""
    monkeypatch.delenv("ZENODO_TOKEN", raising=False)
    downloader = AuthorizedZenodoDownloader()
    assert isinstance(downloader, pooch.HTTPDownloader)


def test_authorized_zenodo_downloader_raises_only_on_invoke(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invoking the downloader without a token raises OSError."""
    monkeypatch.delenv("ZENODO_TOKEN", raising=False)
    downloader = AuthorizedZenodoDownloader()
    with pytest.raises(OSError, match="ZENODO_TOKEN"):
        downloader("http://example.com", "/tmp/out", None)


def test_authorized_zenodo_downloader_injects_bearer_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When a token is set, invocation injects the bearer header and delegates."""
    monkeypatch.setenv("ZENODO_TOKEN", "secret-123")
    downloader = AuthorizedZenodoDownloader()
    with patch.object(pooch.HTTPDownloader, "__call__", return_value=None) as mock_super:
        downloader("http://example.com", "/tmp/out", None)
    assert downloader.kwargs["headers"] == {"Authorization": "Bearer secret-123"}
    mock_super.assert_called_once()
