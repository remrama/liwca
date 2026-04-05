"""Tests for liwca.io — dictionary reading, writing, and merging."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

import liwca
from liwca import io

# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


class TestReadDx:
    """Tests for read_dx (and the internal _read_dic / _read_dicx helpers)."""

    def test_read_dicx_shape(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dx(toy_dicx_path)
        # 16 terms (5 per sport + coach), 3 categories
        assert dx.shape == (16, 3)

    def test_read_dic_shape(self, toy_dic_path: Path) -> None:
        dx = liwca.read_dx(toy_dic_path)
        assert dx.shape == (16, 3)

    def test_index_name(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dx(toy_dicx_path)
        assert dx.index.name == "DicTerm"

    def test_columns_name(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dx(toy_dicx_path)
        assert dx.columns.name == "Category"

    def test_categories(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dx(toy_dicx_path)
        assert sorted(dx.columns) == ["Baseball", "Basketball", "Football"]

    def test_terms_present(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dx(toy_dicx_path)
        assert "hoop" in dx.index
        assert "dunk*" in dx.index
        assert "touchdown*" in dx.index
        assert "pitch*" in dx.index
        assert "coach" in dx.index

    def test_binary_values_only(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dx(toy_dicx_path)
        assert set(dx.values.flat) == {0, 1}

    def test_hoop_is_basketball(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dx(toy_dicx_path)
        assert dx.loc["hoop", "Basketball"] == 1
        assert dx.loc["hoop", "Baseball"] == 0
        assert dx.loc["hoop", "Football"] == 0

    def test_dugout_is_baseball(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dx(toy_dicx_path)
        assert dx.loc["dugout", "Baseball"] == 1
        assert dx.loc["dugout", "Basketball"] == 0

    def test_coach_is_all_three(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dx(toy_dicx_path)
        assert dx.loc["coach", "Basketball"] == 1
        assert dx.loc["coach", "Baseball"] == 1
        assert dx.loc["coach", "Football"] == 1

    def test_sorted_index(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dx(toy_dicx_path)
        assert list(dx.index) == sorted(dx.index)

    def test_sorted_columns(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dx(toy_dicx_path)
        assert list(dx.columns) == sorted(dx.columns)

    def test_dtype(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dx(toy_dicx_path)
        for col in dx.columns:
            assert dx[col].dtype == "int64"

    def test_unsupported_extension(self, tmp_path: Path) -> None:
        fp = tmp_path / "bad.txt"
        fp.write_text("hello")
        with pytest.raises(ValueError, match="Unsupported file extension"):
            liwca.read_dx(fp)

    def test_dic_and_dicx_are_identical(self, toy_dic_path: Path, toy_dicx_path: Path) -> None:
        """Both fixture files represent the same dictionary."""
        dx_dic = liwca.read_dx(toy_dic_path)
        dx_dicx = liwca.read_dx(toy_dicx_path)
        pd.testing.assert_frame_equal(dx_dic, dx_dicx)


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------


class TestWriteDx:
    """Tests for write_dx round-trip."""

    def test_dicx_roundtrip(self, toy_dicx_path: Path, tmp_path: Path) -> None:
        original = liwca.read_dx(toy_dicx_path)
        out_path = tmp_path / "roundtrip.dicx"
        liwca.write_dx(original, out_path)
        reloaded = liwca.read_dx(out_path)
        pd.testing.assert_frame_equal(original, reloaded)

    def test_dic_roundtrip(self, toy_dicx_path: Path, tmp_path: Path) -> None:
        """Read from dicx, write as dic, read back — should be identical."""
        original = liwca.read_dx(toy_dicx_path)
        out_path = tmp_path / "roundtrip.dic"
        liwca.write_dx(original, out_path)
        reloaded = liwca.read_dx(out_path)
        pd.testing.assert_frame_equal(original, reloaded)

    def test_unsupported_extension(self, toy_dicx_path: Path, tmp_path: Path) -> None:
        dx = liwca.read_dx(toy_dicx_path)
        with pytest.raises(ValueError, match="Unsupported file extension"):
            liwca.write_dx(dx, tmp_path / "bad.json")


# ---------------------------------------------------------------------------
# Merging
# ---------------------------------------------------------------------------


class TestMergeDx:
    """Tests for merge_dx."""

    def test_split_and_rejoin(self, toy_dicx_path: Path) -> None:
        """Split a dictionary by columns, merge back, get the original."""
        dx = liwca.read_dx(toy_dicx_path)
        dx_a = dx[["Basketball"]]
        dx_b = dx[["Baseball", "Football"]]
        merged = liwca.merge_dx([dx_a, dx_b])
        pd.testing.assert_frame_equal(merged, dx)

    def test_union_of_categories(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dx(toy_dicx_path)
        dx_a = dx[["Basketball"]]
        dx_b = dx[["Football"]]
        merged = liwca.merge_dx([dx_a, dx_b])
        assert sorted(merged.columns) == ["Basketball", "Football"]

    def test_fills_missing_terms_with_zero(self, toy_dicx_path: Path) -> None:
        """Merging subsets with different term coverage fills gaps with 0."""
        dx = liwca.read_dx(toy_dicx_path)
        # Basketball terms only
        bball = dx[dx["Basketball"] == 1][["Basketball"]]
        # Baseball terms only
        base = dx[dx["Baseball"] == 1][["Baseball"]]
        merged = liwca.merge_dx([bball, base])
        # "hoop" is basketball-only — its Baseball value should be 0
        assert merged.loc["hoop", "Baseball"] == 0
        # "dugout" is baseball-only — its Basketball value should be 0
        assert merged.loc["dugout", "Basketball"] == 0


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------


class TestListAvailable:
    """Tests for list_available."""

    def test_returns_sorted_list(self) -> None:
        result = liwca.list_available()
        assert isinstance(result, list)
        assert result == sorted(result)

    def test_contains_known_dictionaries(self) -> None:
        result = liwca.list_available()
        for name in ("bigtwo_a", "bigtwo_b", "honor", "mystical", "sleep", "threat"):
            assert name in result

    def test_all_strings(self) -> None:
        result = liwca.list_available()
        assert all(isinstance(name, str) for name in result)


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------


class TestFetchPath:
    """Tests for fetch_path."""

    def test_not_in_registry(self) -> None:
        with pytest.raises(ValueError, match="not found in registry"):
            liwca.fetch_path("nonexistent_dictionary_xyz")

    def test_download_error_wraps_as_valueerror(self) -> None:
        """Download failures are wrapped in ValueError with the dictionary name."""
        # Use first registry entry (any will do; the mock prevents actual download)
        dic_name = Path(next(iter(io._pup.registry_files))).stem
        with patch.object(io._pup, "fetch", side_effect=ConnectionError("no internet")):
            with pytest.raises(ValueError, match="Failed to download dictionary"):
                liwca.fetch_path(dic_name)


class TestFetchDx:
    """Tests for fetch_dx error handling (mocked, no network required)."""

    def test_not_in_registry(self) -> None:
        with pytest.raises(ValueError, match="not found in registry"):
            liwca.fetch_dx("nonexistent_dictionary_xyz")

    def test_schema_error_wraps_as_valueerror(self, toybad_dicx_path: Path) -> None:
        """SchemaError from read_dx is wrapped in ValueError, not re-raised as SchemaError.

        toybad.dicx is a valid CSV that parses fine but has uppercase terms,
        which fails the schema's islower() check inside read_dx.
        """
        with patch.object(io, "fetch_path", return_value=str(toybad_dicx_path)):
            with pytest.raises(ValueError, match="Error reading dictionary"):
                liwca.fetch_dx("toybad")

    def test_unsupported_format_without_reader(self, tmp_path: Path) -> None:
        """Fetched file with unsupported extension and no custom reader raises ValueError."""
        fake_file = tmp_path / "weird.json"
        fake_file.write_text("{}")
        with patch.object(io, "fetch_path", return_value=str(fake_file)):
            with pytest.raises(ValueError, match="no registered reader"):
                liwca.fetch_dx("weird")
