from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from conftest import FROZEN_NOW
from ingestion.cleaning import CLEAN_COLUMNS, build_clean_dataframe


def test_clean_dataframe_shape_and_columns(clean_df):
    assert len(clean_df) == 24
    assert list(clean_df.columns) == CLEAN_COLUMNS
    assert clean_df["paper_id"].is_unique
    assert clean_df["published"].is_monotonic_decreasing


def test_age_days_is_run_date_minus_published(clean_df):
    row = clean_df.iloc[0]
    expected = (FROZEN_NOW.date() - datetime.fromisoformat(row["published"]).date()).days
    assert row["age_days"] == expected


def test_text_for_embedding_has_five_parts(clean_df):
    lines = clean_df.iloc[0]["text_for_embedding"].split("\n")
    assert [line.split(":")[0] for line in lines] == ["Title", "Authors", "Published", "Categories", "Summary"]


def test_dedup_keeps_most_recently_updated(records):
    old = replace(records[0], title="Old title", updated="2020-01-01")
    df = build_clean_dataframe([old, records[0]], FROZEN_NOW)
    assert len(df) == 1 and df.iloc[0]["title"] == records[0].title


def test_invalid_rows_dropped_and_text_normalized(records):
    bad_date = replace(records[1], paper_id="10.1/bad-date", published="not a date")
    blank = replace(records[2], paper_id="10.1/blank", summary="   ")
    messy = replace(records[3], title="  Messy \n title ", authors=["A", "A", " ", None], updated="")
    df = build_clean_dataframe([bad_date, blank, messy], FROZEN_NOW.replace(tzinfo=None))
    assert list(df["paper_id"]) == [records[3].paper_id]
    assert df.iloc[0]["title"] == "Messy title"
    assert df.iloc[0]["authors"] == ["A"]
    assert df.iloc[0]["updated"] == df.iloc[0]["published"]


def test_empty_input_returns_empty_frame():
    df = build_clean_dataframe([], FROZEN_NOW)
    assert df.empty and list(df.columns) == CLEAN_COLUMNS
