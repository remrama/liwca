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
        for name in ("bigtwo", "honor", "mystical", "sleep", "threat"):
            assert name in result

    def test_all_strings(self) -> None:
        result = liwca.list_available()
        assert all(isinstance(name, str) for name in result)


class TestGetDictInfo:
    """Tests for get_dict_info."""

    def test_unknown_name_raises(self) -> None:
        with pytest.raises(ValueError, match="not found"):
            liwca.get_dict_info("nonexistent_dictionary_xyz")

    def test_returns_dict_info(self) -> None:
        info = liwca.get_dict_info("threat")
        assert info.description


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------


class TestFetchPath:
    """Tests for fetch_path."""

    def test_not_in_catalogue(self) -> None:
        with pytest.raises(ValueError, match="not found"):
            liwca.fetch_path("nonexistent_dictionary_xyz")

    def test_download_error_wraps_as_valueerror(self) -> None:
        """Download failures are wrapped in ValueError with the dictionary name."""
        dic_name = liwca.list_available()[0]
        with patch.object(io._pup, "fetch", side_effect=ConnectionError("no internet")):
            with pytest.raises(ValueError, match="Failed to download dictionary"):
                liwca.fetch_path(dic_name)


class TestFetchDx:
    """Tests for fetch_dx error handling (mocked, no network required)."""

    def test_not_in_catalogue(self) -> None:
        with pytest.raises(ValueError, match="not found"):
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

    def test_version_error_on_non_versioned(self) -> None:
        """Passing version= to a non-versioned dictionary raises ValueError."""
        with pytest.raises(ValueError, match="not versioned"):
            liwca.fetch_dx("sleep", version="1.0")

    def test_invalid_version_for_versioned_dict(self) -> None:
        """Passing an invalid version for a versioned dictionary raises ValueError."""
        with pytest.raises(ValueError, match="not available"):
            liwca.fetch_dx("bigtwo", version="nonexistent")


# ---------------------------------------------------------------------------
# Registry / Catalogue integrity
# ---------------------------------------------------------------------------


class TestRegistryIntegrity:
    """Tests validating registry.json structure and CATALOGUE consistency."""

    def test_registry_json_has_required_fields(self) -> None:
        """Every entry in registry.json has the required metadata fields."""
        import json
        from importlib.resources import files

        with open(str(files("liwca.data").joinpath("registry.json"))) as f:
            raw = json.load(f)
        required = {"description", "source_url", "source_label"}
        for name, entry in raw.items():
            missing = required - entry.keys()
            assert not missing, f"'{name}' missing required fields: {missing}"
            # Flat entries need filename/hash/url; versioned need versions/default_version
            if "versions" in entry:
                assert "default_version" in entry, f"'{name}' versioned but no default_version"
                for ver, vdata in entry["versions"].items():
                    for field in ("filename", "hash", "url"):
                        assert field in vdata, f"'{name}' version '{ver}' missing '{field}'"
            else:
                for field in ("filename", "hash", "url"):
                    assert field in entry, f"'{name}' flat entry missing '{field}'"

    def test_catalogue_keys_match_json(self) -> None:
        """CATALOGUE keys match the registry.json keys exactly."""
        import json
        from importlib.resources import files

        from liwca._catalogue import CATALOGUE

        with open(str(files("liwca.data").joinpath("registry.json"))) as f:
            raw = json.load(f)
        assert set(CATALOGUE.keys()) == set(raw.keys())

    def test_no_duplicate_filenames(self) -> None:
        """All filenames across all versions must be unique (Pooch cache key)."""
        import json
        from importlib.resources import files

        with open(str(files("liwca.data").joinpath("registry.json"))) as f:
            raw = json.load(f)
        filenames: list[str] = []
        for name, entry in raw.items():
            if "versions" in entry:
                for ver, vdata in entry["versions"].items():
                    filenames.append(vdata["filename"])
            else:
                filenames.append(entry["filename"])
        assert len(filenames) == len(set(filenames)), (
            f"Duplicate filenames in registry.json: "
            f"{[f for f in filenames if filenames.count(f) > 1]}"
        )
