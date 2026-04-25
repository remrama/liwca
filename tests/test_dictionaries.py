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
    dictionaries.fetch_emfd,
    dictionaries.fetch_honor,
    dictionaries.fetch_leeq,
    dictionaries.fetch_mystical,
    dictionaries.fetch_sleep,
    dictionaries.fetch_threat,
    dictionaries.fetch_wrad,
]

# Filenames each public fetcher pulls from the shared Pooch registry.
# Used by the registry-subset test below to catch typos like a fetch_*
# function calling _pup.fetch("foo-bar.dic") when the registry key is
# "foo_bar.dic".
_EXPECTED_REGISTRY_KEYS: dict[str, set[str]] = {
    "fetch_bigtwo": {"bigtwo_a.dic", "bigtwo_b.dic"},
    "fetch_emfd": {"mfd2.0.dic"},
    "fetch_honor": {"honor.dic"},
    "fetch_leeq": {"leeq.tsv"},
    "fetch_mystical": {"mystical.xlsx"},
    "fetch_sleep": {"sleep.tsv"},
    "fetch_threat": {"threat.txt"},
    "fetch_wrad": {"wrad.Wt"},
}


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
    """Tests validating registry.txt structure and _pup consistency.

    Note: the `_pup` registries for `dictionaries`, `corpora`, and `tables`
    all load the same shared `data/registry.txt`, so the whole-registry
    checks (md5 prefix, no duplicates, urls present) cover all three
    categories at once and don't need to be repeated in the sibling test
    modules.
    """

    def test_dictionary_filenames_registered(self) -> None:
        """Every filename a public dictionary fetcher requests is registered."""
        expected = set().union(*_EXPECTED_REGISTRY_KEYS.values())
        registry = set(dictionaries._pup.registry.keys())
        missing = expected - registry
        assert not missing, f"Dictionary filenames missing from registry: {sorted(missing)}"

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
