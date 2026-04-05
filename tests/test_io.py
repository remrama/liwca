"""Tests for liwca.io — dictionary reading, writing, and merging."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import liwca

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
        assert dx.dtypes.eq("int8").all()

    def test_unsupported_extension(self, tmp_path: Path) -> None:
        fp = tmp_path / "bad.txt"
        fp.write_text("hello")
        with pytest.raises(ValueError, match="Unsupported file extension"):
            liwca.read_dx(fp)

    def test_malformed_dic_no_delimiters(self, tmp_path: Path) -> None:
        """A .dic file without '%' delimiters raises ValueError."""
        fp = tmp_path / "bad.dic"
        fp.write_text("this is not a valid dic file\n")
        with pytest.raises(ValueError, match="expected.*delimiters"):
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
        merged = liwca.merge_dx(dx_a, dx_b)
        pd.testing.assert_frame_equal(merged, dx)

    def test_union_of_categories(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dx(toy_dicx_path)
        dx_a = dx[["Basketball"]]
        dx_b = dx[["Football"]]
        merged = liwca.merge_dx(dx_a, dx_b)
        assert sorted(merged.columns) == ["Basketball", "Football"]

    def test_fills_missing_terms_with_zero(self, toy_dicx_path: Path) -> None:
        """Merging subsets with different term coverage fills gaps with 0."""
        dx = liwca.read_dx(toy_dicx_path)
        # Basketball terms only
        bball = dx[dx["Basketball"] == 1][["Basketball"]]
        # Baseball terms only
        base = dx[dx["Baseball"] == 1][["Baseball"]]
        merged = liwca.merge_dx(bball, base)
        # "hoop" is basketball-only — its Baseball value should be 0
        assert merged.loc["hoop", "Baseball"] == 0
        # "dugout" is baseball-only — its Basketball value should be 0
        assert merged.loc["dugout", "Basketball"] == 0

    def test_error_single_dictionary(self, toy_dicx_path: Path) -> None:
        """Merging a single dictionary raises ValueError."""
        dx = liwca.read_dx(toy_dicx_path)
        with pytest.raises(ValueError, match="at least 2"):
            liwca.merge_dx(dx)

    def test_error_overlapping_categories(self, toy_dicx_path: Path) -> None:
        """Merging dictionaries with shared categories raises ValueError."""
        dx = liwca.read_dx(toy_dicx_path)
        dx_a = dx[["Basketball", "Baseball"]]
        dx_b = dx[["Baseball", "Football"]]
        with pytest.raises(ValueError, match="overlapping categories"):
            liwca.merge_dx(dx_a, dx_b)

    def test_warns_wildcard_overlap(self) -> None:
        """Wildcard in one dict matching a literal in another triggers a warning."""
        import warnings

        dx_a = pd.DataFrame({"CatA": [1]}, index=pd.Index(["sleep*"], name="DicTerm"))
        dx_a.index = dx_a.index.astype("string")
        dx_b = pd.DataFrame({"CatB": [1]}, index=pd.Index(["sleeping"], name="DicTerm"))
        dx_b.index = dx_b.index.astype("string")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            liwca.merge_dx(dx_a, dx_b)
            wildcard_warnings = [x for x in w if "sleep*" in str(x.message)]
            assert len(wildcard_warnings) >= 1
