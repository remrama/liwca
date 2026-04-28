"""Tests for liwca.datasets.tables - fetch functions and registry integrity."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from liwca.datasets import tables

# ---------------------------------------------------------------------------
# Fetch function API
# ---------------------------------------------------------------------------

_FETCH_FUNCTIONS = [
    tables.fetch_liwc2015norms,
    tables.fetch_liwc22norms,
    tables.fetch_psychnorms,
    tables.fetch_scope,
]

# Filenames each public fetcher pulls from the shared Pooch registry.
# Tables-side ``fetch_psychnorms`` / ``fetch_scope`` return only the
# column-classification metadata, so they read just the metadata source
# (CSV for psychNorms, the ``metadata`` sheet of the SCOPE xlsx). The full
# psychnorms.zip and the SCOPE ``data`` sheet are pulled by the per-stem
# fetchers in :mod:`liwca.datasets.dictionaries`.
_EXPECTED_REGISTRY_KEYS: dict[str, set[str]] = {
    "fetch_liwc2015norms": {"liwc2015-norms.xlsx"},
    "fetch_liwc22norms": {"liwc22-norms.xlsx"},
    "fetch_psychnorms": {"psychnorms-metadata.csv"},
    "fetch_scope": {"scope.xlsx"},
}


class TestFetchFunctions:
    """Basic API checks for all fetch functions (no network required)."""

    @pytest.mark.parametrize("fetch_fn", _FETCH_FUNCTIONS)
    def test_callable(self, fetch_fn) -> None:
        assert callable(fetch_fn)

    def test_download_failure_raises(self) -> None:
        """Pooch errors propagate up from fetch functions."""
        with patch.object(tables._pup, "fetch", side_effect=ConnectionError("no internet")):
            with pytest.raises(ConnectionError):
                tables.fetch_liwc22norms()


# ---------------------------------------------------------------------------
# Registry integrity
# ---------------------------------------------------------------------------


class TestRegistryIntegrity:
    """Tests validating that table fetchers reference real registry keys."""

    def test_table_filenames_registered(self) -> None:
        """Every filename a public table fetcher requests is registered."""
        expected = set().union(*_EXPECTED_REGISTRY_KEYS.values())
        registry = set(tables._pup.registry.keys())
        missing = expected - registry
        assert not missing, f"Table filenames missing from registry: {sorted(missing)}"
