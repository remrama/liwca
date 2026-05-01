"""Tests for liwca.datasets._common shared helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pooch
import pytest

from liwca.datasets import corpora, dictionaries, tables
from liwca.datasets._common import AuthorizedDownloader

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
# AuthorizedDownloader: token check must be deferred until pooch actually
# needs to download (so cached fetches succeed without a token).
# ---------------------------------------------------------------------------


def test_authorized_downloader_rejects_unknown_repository() -> None:
    """Construction with an unrecognised repository raises ValueError."""
    with pytest.raises(ValueError, match="repository must be one of"):
        AuthorizedDownloader("dropbox")


@pytest.mark.parametrize("repository", ["zenodo", "osf"])
def test_authorized_downloader_does_not_check_token_eagerly(
    repository: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Constructing the downloader with no token must not raise."""
    monkeypatch.delenv(f"{repository.upper()}_TOKEN", raising=False)
    downloader = AuthorizedDownloader(repository)
    assert isinstance(downloader, pooch.HTTPDownloader)
    assert downloader.token_env_var == f"{repository.upper()}_TOKEN"


@pytest.mark.parametrize("repository", ["zenodo", "osf"])
def test_authorized_downloader_raises_only_on_invoke(
    repository: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Invoking the downloader without a token raises OSError."""
    env_var = f"{repository.upper()}_TOKEN"
    monkeypatch.delenv(env_var, raising=False)
    downloader = AuthorizedDownloader(repository)
    with pytest.raises(OSError, match=env_var):
        downloader("http://example.com", "/tmp/out", None)


@pytest.mark.parametrize("repository", ["zenodo", "osf"])
def test_authorized_downloader_injects_bearer_header(
    repository: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When a token is set, invocation injects the bearer header and delegates."""
    monkeypatch.setenv(f"{repository.upper()}_TOKEN", "secret-123")
    downloader = AuthorizedDownloader(repository)
    with patch.object(pooch.HTTPDownloader, "__call__", return_value=None) as mock_super:
        downloader("http://example.com", "/tmp/out", None)
    assert downloader.kwargs["headers"] == {"Authorization": "Bearer secret-123"}
    mock_super.assert_called_once()
