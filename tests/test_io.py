"""Tests for liwca.io - dictionary creation, reading, writing, and merging."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pandera.errors as pa_errors
import pytest

import liwca

# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------


class TestCreateDx:
    """Tests for create_dx."""

    def test_basic_shape(self) -> None:
        dx = liwca.create_dx({"sport": ["baseball", "hockey"], "weather": ["rain", "snow"]})
        assert dx.shape == (4, 2)

    def test_index_and_columns(self) -> None:
        dx = liwca.create_dx({"a": ["x", "y"], "b": ["y", "z"]})
        assert dx.index.name == "DicTerm"
        assert dx.columns.name == "Category"

    def test_binary_values(self) -> None:
        dx = liwca.create_dx({"cat": ["word"]})
        assert set(dx.values.flat) <= {0, 1}
        assert dx.dtypes.eq("int8").all()

    def test_overlapping_terms(self) -> None:
        dx = liwca.create_dx({"a": ["shared", "only_a"], "b": ["shared", "only_b"]})
        assert dx.loc["shared", "a"] == 1
        assert dx.loc["shared", "b"] == 1
        assert dx.loc["only_a", "b"] == 0
        assert dx.loc["only_b", "a"] == 0

    def test_wildcards(self) -> None:
        dx = liwca.create_dx({"cat": ["abandon*", "hello"]})
        assert "abandon*" in dx.index

    def test_lowercases_terms(self) -> None:
        dx = liwca.create_dx({"cat": ["Hello", "WORLD"]})
        assert "hello" in dx.index
        assert "world" in dx.index

    def test_sorted_output(self) -> None:
        dx = liwca.create_dx({"z_cat": ["b", "a"], "a_cat": ["c"]})
        assert list(dx.index) == sorted(dx.index)
        assert list(dx.columns) == sorted(dx.columns)

    def test_empty_dict_raises(self) -> None:
        with pytest.raises((ValueError, pa_errors.SchemaError)):
            liwca.create_dx({})

    def test_empty_word_list_raises(self) -> None:
        with pytest.raises((ValueError, pa_errors.SchemaError)):
            liwca.create_dx({"cat": []})

    def test_roundtrip_with_write(self, tmp_path: Path) -> None:
        dx = liwca.create_dx({"sport": ["baseball", "hockey"], "weather": ["rain", "snow"]})
        out = tmp_path / "created.dicx"
        liwca.write_dicx(dx, out)
        reloaded = liwca.read_dicx(out)
        pd.testing.assert_frame_equal(dx, reloaded)


# ---------------------------------------------------------------------------
# Reading - binary readers
# ---------------------------------------------------------------------------


class TestReadDicx:
    """Tests for read_dicx (binary .dicx parser)."""

    def test_shape(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dicx(toy_dicx_path)
        # 16 terms (5 per sport + coach), 3 categories
        assert dx.shape == (16, 3)

    def test_index_name(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dicx(toy_dicx_path)
        assert dx.index.name == "DicTerm"

    def test_columns_name(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dicx(toy_dicx_path)
        assert dx.columns.name == "Category"

    def test_categories(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dicx(toy_dicx_path)
        assert sorted(dx.columns) == ["Baseball", "Basketball", "Football"]

    def test_terms_present(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dicx(toy_dicx_path)
        assert "hoop" in dx.index
        assert "dunk*" in dx.index
        assert "touchdown*" in dx.index
        assert "pitch*" in dx.index
        assert "coach" in dx.index

    def test_binary_values_only(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dicx(toy_dicx_path)
        assert set(dx.values.flat) == {0, 1}

    def test_hoop_is_basketball(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dicx(toy_dicx_path)
        assert dx.loc["hoop", "Basketball"] == 1
        assert dx.loc["hoop", "Baseball"] == 0
        assert dx.loc["hoop", "Football"] == 0

    def test_dugout_is_baseball(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dicx(toy_dicx_path)
        assert dx.loc["dugout", "Baseball"] == 1
        assert dx.loc["dugout", "Basketball"] == 0

    def test_coach_is_all_three(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dicx(toy_dicx_path)
        assert dx.loc["coach", "Basketball"] == 1
        assert dx.loc["coach", "Baseball"] == 1
        assert dx.loc["coach", "Football"] == 1

    def test_sorted_index(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dicx(toy_dicx_path)
        assert list(dx.index) == sorted(dx.index)

    def test_sorted_columns(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dicx(toy_dicx_path)
        assert list(dx.columns) == sorted(dx.columns)

    def test_dtype(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dicx(toy_dicx_path)
        assert dx.dtypes.eq("int8").all()

    def test_rejects_numeric_content_with_hint(self, tmp_path: Path) -> None:
        """A weighted-format .dicx parsed as binary raises with a clear hint."""
        fp = tmp_path / "weighted.dicx"
        fp.write_text("DicTerm,sentiment\ngreat,0.5\nawful,-0.7\n")
        with pytest.raises(ValueError, match="read_dicx_weighted"):
            liwca.read_dicx(fp)

    def test_rejects_typo_Y(self, tmp_path: Path) -> None:
        """A typo'd `Y` (not `X`) is flagged, not silently coerced."""
        fp = tmp_path / "typo.dicx"
        fp.write_text("DicTerm,CatA\nfoo,Y\nbar,X\n")
        with pytest.raises(ValueError, match="non-binary values"):
            liwca.read_dicx(fp)


class TestReadDic:
    """Tests for read_dic (binary .dic parser)."""

    def test_shape(self, toy_dic_path: Path) -> None:
        dx = liwca.read_dic(toy_dic_path)
        assert dx.shape == (16, 3)

    def test_dtype(self, toy_dic_path: Path) -> None:
        dx = liwca.read_dic(toy_dic_path)
        assert dx.dtypes.eq("int8").all()

    def test_dic_and_dicx_are_identical(self, toy_dic_path: Path, toy_dicx_path: Path) -> None:
        """Both fixture files represent the same dictionary."""
        dx_dic = liwca.read_dic(toy_dic_path)
        dx_dicx = liwca.read_dicx(toy_dicx_path)
        pd.testing.assert_frame_equal(dx_dic, dx_dicx)

    def test_malformed_no_delimiters(self, tmp_path: Path) -> None:
        """A .dic file without '%' delimiters raises ValueError."""
        fp = tmp_path / "bad.dic"
        fp.write_text("this is not a valid dic file\n")
        with pytest.raises(ValueError, match="expected.*delimiters"):
            liwca.read_dic(fp)


# ---------------------------------------------------------------------------
# Reading - weighted reader
# ---------------------------------------------------------------------------


class TestReadDicxWeighted:
    """Tests for read_dicx_weighted (numeric .dicx parser)."""

    def test_shape(self, toy_weighted_dicx_path: Path) -> None:
        dx = liwca.read_dicx_weighted(toy_weighted_dicx_path)
        assert dx.shape == (5, 3)

    def test_dtype(self, toy_weighted_dicx_path: Path) -> None:
        dx = liwca.read_dicx_weighted(toy_weighted_dicx_path)
        assert dx.dtypes.eq("float64").all()

    def test_signed_values(self, toy_weighted_dicx_path: Path) -> None:
        """Negative weights survive validation (signed allowed)."""
        dx = liwca.read_dicx_weighted(toy_weighted_dicx_path)
        assert (dx.values < 0).any()
        assert (dx.values > 0).any()

    def test_categories_named(self, toy_weighted_dicx_path: Path) -> None:
        dx = liwca.read_dicx_weighted(toy_weighted_dicx_path)
        assert dx.index.name == "DicTerm"
        assert dx.columns.name == "Category"

    def test_rejects_X_markers_with_hint(self, toy_dicx_path: Path) -> None:
        """A binary-format .dicx parsed as weighted raises with a clear hint."""
        with pytest.raises(ValueError, match="read_dicx"):
            liwca.read_dicx_weighted(toy_dicx_path)


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------


class TestWriteDicx:
    """Tests for write_dicx (binary .dicx writer)."""

    def test_roundtrip(self, toy_dicx_path: Path, tmp_path: Path) -> None:
        original = liwca.read_dicx(toy_dicx_path)
        out_path = tmp_path / "roundtrip.dicx"
        liwca.write_dicx(original, out_path)
        reloaded = liwca.read_dicx(out_path)
        pd.testing.assert_frame_equal(original, reloaded)


class TestWriteDic:
    """Tests for write_dic (.dic writer)."""

    def test_roundtrip_via_dic(self, toy_dicx_path: Path, tmp_path: Path) -> None:
        """Read from .dicx, write as .dic, read back -- should be identical."""
        original = liwca.read_dicx(toy_dicx_path)
        out_path = tmp_path / "roundtrip.dic"
        liwca.write_dic(original, out_path)
        reloaded = liwca.read_dic(out_path)
        pd.testing.assert_frame_equal(original, reloaded)


class TestWriteDicxWeighted:
    """Tests for write_dicx_weighted (numeric .dicx writer)."""

    def test_roundtrip(self, toy_weighted_dicx_path: Path, tmp_path: Path) -> None:
        # Read once to bring through the schema (sorted index, normalized dtype),
        # then round-trip and compare against the schema-normalized form.
        original = liwca.read_dicx_weighted(toy_weighted_dicx_path)
        out_path = tmp_path / "weighted.dicx"
        liwca.write_dicx_weighted(original, out_path)
        reloaded = liwca.read_dicx_weighted(out_path)
        pd.testing.assert_frame_equal(original, reloaded)

    def test_signed_values_survive_roundtrip(
        self, toy_weighted_dicx_path: Path, tmp_path: Path
    ) -> None:
        original = liwca.read_dicx_weighted(toy_weighted_dicx_path)
        out_path = tmp_path / "signed.dicx"
        liwca.write_dicx_weighted(original, out_path)
        reloaded = liwca.read_dicx_weighted(out_path)
        assert reloaded.loc["awful", "Negative"] == pytest.approx(-0.7)
        assert reloaded.loc["bad", "Negative"] == pytest.approx(-0.5)


# ---------------------------------------------------------------------------
# Schema rejections
# ---------------------------------------------------------------------------


class TestSchemaRejections:
    """Each schema rejects the wrong shape loudly.

    Note: tests instantiate fresh copies of the schemas because pandera's
    regex-column resolution caches the resolved column set on the schema
    object during validation. Sharing the global schema across tests with
    different column names mutates it and breaks later tests.
    """

    def test_dx_schema_rejects_values_outside_0_1(self) -> None:
        """A binary-typed dict with a stray 2 fails dx_schema."""
        import copy

        bad = pd.DataFrame(
            {"CatA": [1, 2]},
            index=pd.Index(["foo", "bar"], name="DicTerm", dtype="string"),
        ).astype({"CatA": "int8"})
        bad.columns.name = "Category"
        schema = copy.deepcopy(liwca.io.dx_schema)
        with pytest.raises(pa_errors.SchemaError):
            schema.validate(bad)

    def test_dx_weighted_schema_accepts_signed(self, toy_weighted_dx: pd.DataFrame) -> None:
        """The weighted schema accepts negative values."""
        import copy

        schema = copy.deepcopy(liwca.io.dx_weighted_schema)
        validated = schema.validate(toy_weighted_dx)
        assert (validated.values < 0).any()


# ---------------------------------------------------------------------------
# Merging
# ---------------------------------------------------------------------------


class TestMergeDx:
    """Tests for merge_dx."""

    def test_split_and_rejoin(self, toy_dicx_path: Path) -> None:
        """Split a dictionary by columns, merge back, get the original."""
        dx = liwca.read_dicx(toy_dicx_path)
        dx_a = dx[["Basketball"]]
        dx_b = dx[["Baseball", "Football"]]
        merged = liwca.merge_dx(dx_a, dx_b)
        pd.testing.assert_frame_equal(merged, dx)

    def test_union_of_categories(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dicx(toy_dicx_path)
        dx_a = dx[["Basketball"]]
        dx_b = dx[["Football"]]
        merged = liwca.merge_dx(dx_a, dx_b)
        assert sorted(merged.columns) == ["Basketball", "Football"]

    def test_fills_missing_terms_with_zero(self, toy_dicx_path: Path) -> None:
        """Merging subsets with different term coverage fills gaps with 0."""
        dx = liwca.read_dicx(toy_dicx_path)
        # Basketball terms only
        bball = dx[dx["Basketball"] == 1][["Basketball"]]
        # Baseball terms only
        base = dx[dx["Baseball"] == 1][["Baseball"]]
        merged = liwca.merge_dx(bball, base)
        # "hoop" is basketball-only - its Baseball value should be 0
        assert merged.loc["hoop", "Baseball"] == 0
        # "dugout" is baseball-only - its Basketball value should be 0
        assert merged.loc["dugout", "Basketball"] == 0

    def test_error_single_dictionary(self, toy_dicx_path: Path) -> None:
        """Merging a single dictionary raises ValueError."""
        dx = liwca.read_dicx(toy_dicx_path)
        with pytest.raises(ValueError, match="at least 2"):
            liwca.merge_dx(dx)

    def test_error_overlapping_categories(self, toy_dicx_path: Path) -> None:
        """Merging dictionaries with shared categories raises ValueError."""
        dx = liwca.read_dicx(toy_dicx_path)
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

    def test_weighted_only(self, toy_weighted_dx: pd.DataFrame) -> None:
        """Merging two weighted dicts validates against dx_weighted_schema."""
        dx_a = toy_weighted_dx[["Negative"]]
        dx_b = toy_weighted_dx[["Positive"]]
        merged = liwca.merge_dx(dx_a, dx_b)
        assert merged.dtypes.eq("float64").all()
        assert sorted(merged.columns) == ["Negative", "Positive"]

    def test_binary_promoted_when_any_weighted(
        self, toy_dicx_path: Path, toy_weighted_dx: pd.DataFrame
    ) -> None:
        """Mixed binary + weighted inputs promote everything to float64."""
        dx_binary = liwca.read_dicx(toy_dicx_path)[["Basketball"]]
        dx_weighted = toy_weighted_dx[["Negative"]]
        merged = liwca.merge_dx(dx_binary, dx_weighted)
        assert merged.dtypes.eq("float64").all()


# ---------------------------------------------------------------------------
# Dropping categories
# ---------------------------------------------------------------------------


class TestDropCategory:
    """Tests for drop_category."""

    def test_drop_single_string(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dicx(toy_dicx_path)
        result = liwca.drop_category(dx, "Football")
        assert "Football" not in result.columns
        assert sorted(result.columns) == ["Baseball", "Basketball"]

    def test_drop_multiple(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dicx(toy_dicx_path)
        result = liwca.drop_category(dx, ["Baseball", "Football"])
        assert list(result.columns) == ["Basketball"]

    def test_orphaned_terms_removed(self, toy_dicx_path: Path) -> None:
        """Terms belonging only to dropped categories are removed."""
        dx = liwca.read_dicx(toy_dicx_path)
        result = liwca.drop_category(dx, ["Baseball", "Football"])
        # "dugout" is Baseball-only, "quarterback" is Football-only
        assert "dugout" not in result.index
        assert "quarterback" not in result.index

    def test_shared_terms_kept(self, toy_dicx_path: Path) -> None:
        """Terms shared with remaining categories survive."""
        dx = liwca.read_dicx(toy_dicx_path)
        result = liwca.drop_category(dx, "Football")
        # "coach" belongs to all three categories, so it stays
        assert "coach" in result.index

    def test_schema_valid(self, toy_dicx_path: Path) -> None:
        """Output passes dx_schema validation (index, dtypes, sorted)."""
        dx = liwca.read_dicx(toy_dicx_path)
        result = liwca.drop_category(dx, "Football")
        assert result.index.name == "DicTerm"
        assert result.columns.name == "Category"
        assert (result.dtypes == "int8").all()

    def test_missing_category_raises(self, toy_dicx_path: Path) -> None:
        dx = liwca.read_dicx(toy_dicx_path)
        with pytest.raises(KeyError, match="NoSuchCategory"):
            liwca.drop_category(dx, "NoSuchCategory")

    def test_original_unchanged(self, toy_dicx_path: Path) -> None:
        """Dropping does not mutate the input DataFrame."""
        dx = liwca.read_dicx(toy_dicx_path)
        original_shape = dx.shape
        liwca.drop_category(dx, "Football")
        assert dx.shape == original_shape

    def test_weighted_preserves_dtype(self, toy_weighted_dx: pd.DataFrame) -> None:
        """Dropping from a weighted dict keeps float64 dtype."""
        result = liwca.drop_category(toy_weighted_dx, "Neutral")
        assert result.dtypes.eq("float64").all()
        # Weighted dicts don't drop terms-with-no-categories: even after
        # dropping Neutral, "ok" (which was Neutral-only) stays at 0.0.
        assert "ok" in result.index

    def test_mixed_dtype_raises_typeerror(self) -> None:
        """A DataFrame with mixed int8/float64 columns raises TypeError."""
        mixed = pd.DataFrame(
            {"A": [1], "B": [0.5]},
            index=pd.Index(["foo"], name="DicTerm", dtype="string"),
        ).astype({"A": "int8", "B": "float64"})
        mixed.columns.name = "Category"
        # Sanity: the fixture really has mixed dtypes.
        assert set(mixed.dtypes.astype(str)) == {"int8", "float64"}
        with pytest.raises(TypeError, match="all-int8.*all-float64"):
            liwca.drop_category(mixed, "B")
