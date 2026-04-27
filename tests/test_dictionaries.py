"""Tests for liwca.datasets.dictionaries - fetch functions and registry integrity."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from liwca.datasets import dictionaries
from liwca.datasets.dictionaries import BuildDicx

# ---------------------------------------------------------------------------
# Fetch function API
# ---------------------------------------------------------------------------

_FETCH_FUNCTIONS = [
    dictionaries.fetch_bigtwo,
    dictionaries.fetch_emfd,
    dictionaries.fetch_empath,
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
    "fetch_empath": {"empath.tsv"},
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
        with patch.object(dictionaries._pup, "fetch", return_value="/fake/bigtwo_a.dicx") as mock:
            with patch("liwca.datasets.dictionaries.read_dx"):
                try:
                    dictionaries.fetch_bigtwo()
                except Exception:
                    pass
        # First positional arg is the registry filename; kwargs include the processor.
        assert mock.call_args.args[0] == "bigtwo_a.dic"

    def test_fetch_bigtwo_version_b(self) -> None:
        with patch.object(dictionaries._pup, "fetch", return_value="/fake/bigtwo_b.dicx") as mock:
            with patch("liwca.datasets.dictionaries.read_dx"):
                try:
                    dictionaries.fetch_bigtwo(version="b")
                except Exception:
                    pass
        assert mock.call_args.args[0] == "bigtwo_b.dic"

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


# ---------------------------------------------------------------------------
# BuildDicx processor
# ---------------------------------------------------------------------------


class TestBuildDicx:
    """Tests for the BuildDicx pooch processor."""

    def _df(self) -> pd.DataFrame:
        # Minimal dx-shaped DataFrame - lowercase string index named DicTerm,
        # binary int8 column named under axis "Category".
        df = pd.DataFrame(
            {"foo": [1, 0]},
            index=pd.Index(["alpha", "beta"], name="DicTerm", dtype="string"),
        ).rename_axis("Category", axis=1)
        return df.astype("int8")

    def test_cold_call_writes_dicx_and_returns_path(self, tmp_path: Path) -> None:
        """First-time invocation runs build_fn, writes .dicx, returns its path."""
        source = tmp_path / "src.tsv"
        source.write_text("ignored")
        build_called = []

        def build(p: Path) -> pd.DataFrame:
            build_called.append(p)
            return self._df()

        proc = BuildDicx(build, "test.dicx")
        result = proc(str(source), "download", None)
        assert build_called == [Path(source)]
        assert (tmp_path / "test.dicx").exists()
        assert result == str(tmp_path / "test.dicx")

    def test_warm_call_returns_cached_without_calling_build(self, tmp_path: Path) -> None:
        """When .dicx already exists and action=='fetch', skip build_fn."""
        source = tmp_path / "src.tsv"
        source.write_text("ignored")
        cached = tmp_path / "test.dicx"
        cached.write_text("DicTerm,foo\nalpha,X\nbeta,\n")

        def build(p: Path) -> pd.DataFrame:
            raise AssertionError("build_fn should not be called on warm path")

        proc = BuildDicx(build, "test.dicx")
        result = proc(str(source), "fetch", None)
        assert result == str(cached)

    def test_action_download_rebuilds_even_if_cached(self, tmp_path: Path) -> None:
        """A redownload (action!='fetch') always rebuilds, replacing stale cache."""
        source = tmp_path / "src.tsv"
        source.write_text("ignored")
        cached = tmp_path / "test.dicx"
        cached.write_text("STALE")
        build_called = []

        def build(p: Path) -> pd.DataFrame:
            build_called.append(p)
            return self._df()

        proc = BuildDicx(build, "test.dicx")
        proc(str(source), "download", None)
        assert build_called == [Path(source)]
        # Cache file was overwritten
        assert "STALE" not in cached.read_text()


# ---------------------------------------------------------------------------
# path() resolver
# ---------------------------------------------------------------------------


class TestPathResolver:
    """Tests for dictionaries.path() name → cached .dicx Path resolver."""

    def test_unknown_name_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown dictionary 'nonexistent'"):
            dictionaries.path("nonexistent")

    def test_wrad_raises_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError, match="continuous values"):
            dictionaries.path("wrad")

    def test_returns_friendly_stem_path(self) -> None:
        """For most fetchers, path returns <cache>/<name>.dicx after fetcher runs."""
        with patch.object(dictionaries, "fetch_sleep") as mock_fetch:
            result = dictionaries.path("sleep")
        mock_fetch.assert_called_once_with()
        assert isinstance(result, Path)
        assert result.name == "sleep.dicx"
        assert result.parent == Path(dictionaries._pup.path)

    def test_bigtwo_default_version_is_a(self) -> None:
        with patch.object(dictionaries, "fetch_bigtwo") as mock_fetch:
            result = dictionaries.path("bigtwo")
        mock_fetch.assert_called_once_with()
        assert result.name == "bigtwo_a.dicx"

    def test_bigtwo_version_b(self) -> None:
        with patch.object(dictionaries, "fetch_bigtwo") as mock_fetch:
            result = dictionaries.path("bigtwo", version="b")
        mock_fetch.assert_called_once_with(version="b")
        assert result.name == "bigtwo_b.dicx"
