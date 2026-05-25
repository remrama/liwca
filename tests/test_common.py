"""Tests for liwca.datasets._common shared helpers."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd
import pytest

from liwca.datasets import corpora, dictionaries, tables
from liwca.datasets._common import BuildDicx, CacheCsv, UnzipToCsv

_GET_LOCATION_CASES = [
    ("corpora", corpora.get_location),
    ("dictionaries", dictionaries.get_location),
    ("tables", tables.get_location),
]


@pytest.mark.parametrize("category,get_location", _GET_LOCATION_CASES)
def test_get_location(category: str, get_location) -> None:
    """Per-module get_location() returns a Path ending in the category name."""
    loc = get_location()
    assert isinstance(loc, Path)
    assert loc.name == category


# ---------------------------------------------------------------------------
# UnzipToCsv processor
# ---------------------------------------------------------------------------


def _toy_df() -> pd.DataFrame:
    return pd.DataFrame({"text": ["a", "b"]}, index=pd.Index(["x", "y"], name="key"))


class TestUnzipToCsv:
    """UnzipToCsv: unzip + parse on cold call, return cached CSV on warm fetch."""

    def _make_zip(self, tmp_path: Path) -> Path:
        zip_path = tmp_path / "src.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("member.txt", "ignored content")
        return zip_path

    def test_cold_call_unzips_builds_and_caches(self, tmp_path: Path) -> None:
        src = self._make_zip(tmp_path)
        seen: list[list[Path]] = []

        def build(members: list[Path]) -> pd.DataFrame:
            seen.append(members)
            return _toy_df()

        proc = UnzipToCsv(build, "cached.csv", members=["member.txt"])
        result = proc(str(src), "download", None)
        assert seen and seen[0][0].name == "member.txt"
        cached = tmp_path / "cached.csv"
        assert cached.exists()
        assert result == str(cached)

    def test_warm_call_returns_cached_without_unzipping(self, tmp_path: Path) -> None:
        src = self._make_zip(tmp_path)
        cached = tmp_path / "cached.csv"
        cached.write_text("key,text\nx,a\n")

        def build(members: list[Path]) -> pd.DataFrame:
            raise AssertionError("build_fn should not run on warm fetch")

        proc = UnzipToCsv(build, "cached.csv")
        result = proc(str(src), "fetch", None)
        assert result == str(cached)


# ---------------------------------------------------------------------------
# CacheCsv processor
# ---------------------------------------------------------------------------


class TestCacheCsv:
    """CacheCsv: parse the source on cold call, return cached CSV on warm fetch."""

    def test_cold_call_parses_and_caches(self, tmp_path: Path) -> None:
        src = tmp_path / "src.tsv"
        src.write_text("ignored")
        seen: list[Path] = []

        def build(path: Path) -> pd.DataFrame:
            seen.append(path)
            return _toy_df()

        proc = CacheCsv(build, "out.csv")
        result = proc(str(src), "download", None)
        assert seen == [src]
        cached = tmp_path / "out.csv"
        assert cached.exists()
        assert result == str(cached)

    def test_warm_call_skips_build_fn(self, tmp_path: Path) -> None:
        src = tmp_path / "src.tsv"
        src.write_text("ignored")
        cached = tmp_path / "out.csv"
        cached.write_text("key,text\nx,a\n")

        def build(path: Path) -> pd.DataFrame:
            raise AssertionError("build_fn should not run on warm fetch")

        proc = CacheCsv(build, "out.csv")
        result = proc(str(src), "fetch", None)
        assert result == str(cached)


# ---------------------------------------------------------------------------
# BuildDicx weighted variant
# ---------------------------------------------------------------------------


class TestBuildDicxWeighted:
    """BuildDicx with weighted=True writes via write_dicx_weighted."""

    def test_writes_weighted_dicx_with_signed_floats(self, tmp_path: Path) -> None:
        src = tmp_path / "src.tsv"
        src.write_text("ignored")

        def build(path: Path) -> pd.DataFrame:
            df = pd.DataFrame(
                {"sentiment": [-0.5, 0.9]},
                index=pd.Index(["bad", "great"], name="DicTerm", dtype="string"),
            ).astype("float64")
            df.columns.name = "Category"
            return df

        proc = BuildDicx(build, "weighted.dicx", weighted=True)
        result = proc(str(src), "download", None)
        cached = tmp_path / "weighted.dicx"
        assert cached.exists()
        # Loading via read_dicx_weighted round-trips the signed floats.
        import liwca

        dx = liwca.read_dicx_weighted(cached)
        assert dx.loc["bad", "sentiment"] == pytest.approx(-0.5)
        assert dx.loc["great", "sentiment"] == pytest.approx(0.9)
        assert result == str(cached)
