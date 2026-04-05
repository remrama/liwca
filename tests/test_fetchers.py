"""Tests for liwca.fetchers — listing, metadata, fetching, and registry integrity."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

import liwca
from liwca import fetchers

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
        with patch.object(fetchers._pup, "fetch", side_effect=ConnectionError("no internet")):
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
        with patch.object(fetchers, "fetch_path", return_value=str(toybad_dicx_path)):
            with pytest.raises(ValueError, match="Error reading dictionary"):
                liwca.fetch_dx("toybad")

    def test_unsupported_format_without_reader(self, tmp_path: Path) -> None:
        """Fetched file with unsupported extension and no custom reader raises ValueError."""
        fake_file = tmp_path / "weird.json"
        fake_file.write_text("{}")
        with patch.object(fetchers, "fetch_path", return_value=str(fake_file)):
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
        required = {"description", "source_url", "source_label", "citations"}
        for name, entry in raw.items():
            missing = required - entry.keys()
            assert not missing, f"'{name}' missing required fields: {missing}"
            # Citations must be a non-empty list of strings
            citations = entry["citations"]
            assert isinstance(citations, list) and len(citations) > 0, (
                f"'{name}' must have at least one citation in 'citations'"
            )
            for cite in citations:
                assert isinstance(cite, str) and len(cite) > 0, (
                    f"'{name}' has empty or non-string citation entry"
                )
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
