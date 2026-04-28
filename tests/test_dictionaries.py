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
    dictionaries.fetch_psychnorms,
    dictionaries.fetch_scope,
    dictionaries.fetch_sleep,
    dictionaries.fetch_threat,
    dictionaries.fetch_wrad,
]

# Filenames each public fetcher pulls from the shared Pooch registry.
# Used by the registry-subset test below to catch typos like a fetch_*
# function calling _pup.fetch("foo-bar.dic") when the registry key is
# "foo_bar.dic".
_EXPECTED_REGISTRY_KEYS: dict[str, set[str]] = {
    "fetch_bigtwo": {"bigtwo-va.dic", "bigtwo-vb.dic"},
    "fetch_emfd": {"emfd.dic"},
    "fetch_empath": {"empath.tsv"},
    "fetch_honor": {"honor.dic"},
    "fetch_leeq": {"leeq.tsv"},
    "fetch_mystical": {"mystical.xlsx"},
    # fetch_psychnorms reads `psychnorms.zip` for word-level scores and
    # `psychnorms-metadata.csv` for stem validation.
    "fetch_psychnorms": {"psychnorms.zip", "psychnorms-metadata.csv"},
    "fetch_scope": {"scope.xlsx"},
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
        """Calling fetch_bigtwo() without version uses 'a' (bigtwo-va.dic)."""
        with patch.object(dictionaries._pup, "fetch", return_value="/fake/bigtwo-va.dicx") as mock:
            with patch("liwca.datasets.dictionaries.read_dicx"):
                try:
                    dictionaries.fetch_bigtwo()
                except Exception:
                    pass
        # First positional arg is the registry filename; kwargs include the processor.
        assert mock.call_args.args[0] == "bigtwo-va.dic"

    def test_fetch_bigtwo_version_b(self) -> None:
        with patch.object(dictionaries._pup, "fetch", return_value="/fake/bigtwo-vb.dicx") as mock:
            with patch("liwca.datasets.dictionaries.read_dicx"):
                try:
                    dictionaries.fetch_bigtwo(version="b")
                except Exception:
                    pass
        assert mock.call_args.args[0] == "bigtwo-vb.dic"

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

    def test_wrad_returns_weighted_dicx_path(self) -> None:
        """fetch_wrad now caches as a weighted .dicx; path() should resolve it."""
        with patch.object(dictionaries, "fetch_wrad") as mock_fetch:
            result = dictionaries.path("wrad")
        mock_fetch.assert_called_once_with()
        assert result.name == "wrad.dicx"

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
        assert result.name == "bigtwo-va.dicx"

    def test_bigtwo_version_b(self) -> None:
        with patch.object(dictionaries, "fetch_bigtwo") as mock_fetch:
            result = dictionaries.path("bigtwo", version="b")
        mock_fetch.assert_called_once_with(version="b")
        assert result.name == "bigtwo-vb.dicx"

    def test_scope_lowercases_stem_in_cache_name(self) -> None:
        """SCOPE stems are PascalCase upstream but the .dicx filename is lowercased."""
        with patch.object(dictionaries, "fetch_scope") as mock_fetch:
            result = dictionaries.path("scope", stem="Conc_Brys")
        mock_fetch.assert_called_once_with(stem="Conc_Brys")
        assert result.name == "scope-conc_brys.dicx"

    def test_psychnorms_path(self) -> None:
        with patch.object(dictionaries, "fetch_psychnorms") as mock_fetch:
            result = dictionaries.path("psychnorms", stem="concreteness_brysbaert")
        mock_fetch.assert_called_once_with(stem="concreteness_brysbaert")
        assert result.name == "psychnorms-concreteness_brysbaert.dicx"


# ---------------------------------------------------------------------------
# Metabase stem resolution (SCOPE / psychNorms)
# ---------------------------------------------------------------------------


class TestMetabaseStemResolution:
    """Stem-validation behaviour for fetch_scope / fetch_psychnorms.

    These tests bypass the network by patching the memoised stem maps
    directly; the underlying metadata files are exercised via test_remote.py.
    """

    def test_resolve_scope_stem_is_case_insensitive(self) -> None:
        with patch.object(dictionaries, "_scope_stems", return_value={"conc_brys": "Conc_Brys"}):
            assert dictionaries._resolve_scope_stem("Conc_Brys") == "Conc_Brys"
            assert dictionaries._resolve_scope_stem("conc_brys") == "Conc_Brys"
            assert dictionaries._resolve_scope_stem("CONC_BRYS") == "Conc_Brys"

    def test_resolve_scope_stem_unknown_raises(self) -> None:
        with patch.object(dictionaries, "_scope_stems", return_value={"conc_brys": "Conc_Brys"}):
            with pytest.raises(ValueError, match="Unknown SCOPE stem"):
                dictionaries._resolve_scope_stem("not_a_real_stem")

    def test_resolve_psychnorms_stem_is_case_insensitive(self) -> None:
        with patch.object(
            dictionaries, "_psychnorms_stems", return_value=frozenset({"concreteness_brysbaert"})
        ):
            assert (
                dictionaries._resolve_psychnorms_stem("Concreteness_Brysbaert")
                == "concreteness_brysbaert"
            )

    def test_resolve_psychnorms_stem_unknown_raises(self) -> None:
        with patch.object(
            dictionaries, "_psychnorms_stems", return_value=frozenset({"concreteness_brysbaert"})
        ):
            with pytest.raises(ValueError, match="Unknown psychNorms stem"):
                dictionaries._resolve_psychnorms_stem("not_a_real_stem")

    def test_list_scope_stems_returns_sorted_lowercase(self) -> None:
        with patch.object(
            dictionaries,
            "_scope_stems",
            return_value={"freq_hal": "Freq_HAL", "conc_brys": "Conc_Brys"},
        ):
            stems = dictionaries.list_scope_stems()
        assert stems == sorted(stems)
        assert all(s == s.lower() for s in stems)

    def test_list_psychnorms_stems_returns_sorted(self) -> None:
        with patch.object(
            dictionaries,
            "_psychnorms_stems",
            return_value=frozenset({"frequency_lund", "concreteness_brysbaert"}),
        ):
            stems = dictionaries.list_psychnorms_stems()
        assert stems == sorted(stems)
