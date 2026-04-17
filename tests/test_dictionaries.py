"""Tests for liwca.datasets.dictionaries - fetch functions and registry integrity."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from liwca.datasets import dictionaries

# ---------------------------------------------------------------------------
# Fetch function API
# ---------------------------------------------------------------------------

_FETCH_FUNCTIONS = [
    dictionaries.fetch_bigtwo,
    dictionaries.fetch_honor,
    dictionaries.fetch_mystical,
    dictionaries.fetch_sleep,
    dictionaries.fetch_threat,
]


class TestFetchFunctions:
    """Basic API checks for all fetch functions (no network required)."""

    @pytest.mark.parametrize("fetch_fn", _FETCH_FUNCTIONS)
    def test_callable(self, fetch_fn) -> None:
        assert callable(fetch_fn)

    def test_fetch_bigtwo_invalid_version(self) -> None:
        with pytest.raises(ValueError, match="version must be one of"):
            dictionaries.fetch_bigtwo(version="nonexistent")

    def test_fetch_bigtwo_default_version_is_a(self) -> None:
        """Calling fetch_bigtwo() without version uses 'a' (bigtwo_a.dic)."""
        with patch.object(dictionaries._pup, "fetch", return_value="/fake/bigtwo_a.dic") as mock:
            with patch("liwca.datasets.dictionaries.read_dx"):
                try:
                    dictionaries.fetch_bigtwo()
                except Exception:
                    pass
        mock.assert_called_with("bigtwo_a.dic")

    def test_fetch_bigtwo_version_b(self) -> None:
        with patch.object(dictionaries._pup, "fetch", return_value="/fake/bigtwo_b.dic") as mock:
            with patch("liwca.datasets.dictionaries.read_dx"):
                try:
                    dictionaries.fetch_bigtwo(version="b")
                except Exception:
                    pass
        mock.assert_called_with("bigtwo_b.dic")

    def test_download_failure_raises(self) -> None:
        """Pooch errors propagate up from fetch functions."""
        with patch.object(dictionaries._pup, "fetch", side_effect=ConnectionError("no internet")):
            with pytest.raises(ConnectionError):
                dictionaries.fetch_honor()


# ---------------------------------------------------------------------------
# Registry integrity
# ---------------------------------------------------------------------------


class TestRegistryIntegrity:
    """Tests validating registry.txt structure and _pup consistency."""

    def test_all_filenames_registered(self) -> None:
        """All expected filenames are in the Pooch registry."""
        expected = {
            "bigtwo_a.dic",
            "bigtwo_b.dic",
            "honor.dic",
            "mystical.xlsx",
            "sleep.tsv",
            "threat.txt",
        }
        assert expected == set(dictionaries._pup.registry.keys())

    def test_all_hashes_are_md5(self) -> None:
        """All registered hashes use md5."""
        for fname, hash_val in dictionaries._pup.registry.items():
            assert hash_val.startswith("md5:"), (
                f"'{fname}' hash should start with 'md5:'; got {hash_val!r}"
            )

    def test_no_duplicate_filenames(self) -> None:
        filenames = list(dictionaries._pup.registry.keys())
        assert len(filenames) == len(set(filenames))

    def test_all_filenames_have_urls(self) -> None:
        for fname in dictionaries._pup.registry:
            assert fname in dictionaries._pup.urls, f"'{fname}' missing URL in _pup"
