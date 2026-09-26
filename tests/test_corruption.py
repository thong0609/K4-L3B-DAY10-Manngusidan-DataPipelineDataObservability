from __future__ import annotations

from core.utils import read_json
from ingestion.corruption import corrupt_clean_dataframe

KINDS = {"drop_latest_records", "blank_summary", "inject_noise", "truncate_title", "stale_date", "duplicate_rows"}


def test_injects_all_six_corruptions_and_logs(clean_df, settings):
    corrupted = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    log = read_json(settings.paths.corruption_log)
    assert set(log["corruption_counts"]) == KINDS
    assert log["input_rows"] == 24 and log["output_rows"] == len(corrupted) == 22
    assert all({"corruption", "paper_id", "before", "after"} <= set(event) for event in log["events"])


def test_corruption_effects(clean_df, settings):
    corrupted = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    latest = set(clean_df.sort_values("published", ascending=False).head(5)["paper_id"])
    assert not latest & set(corrupted["paper_id"])
    assert (corrupted["summary"] == "").sum() >= 3
    assert corrupted["summary"].str.contains("0xDEADBEEF").sum() >= 3
    assert (corrupted["title"].str.len() < 8).sum() >= 3
    assert corrupted["paper_id"].duplicated().sum() == 3
    assert (corrupted["age_days"] > 365).sum() >= 7
    # text_for_embedding duoc rebuild tu du lieu ban
    blank = corrupted[corrupted["summary"] == ""].iloc[0]
    assert blank["text_for_embedding"].endswith("Summary: ")


def test_is_deterministic_and_does_not_mutate_input(clean_df, settings):
    snapshot = clean_df.copy()
    first = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    second = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    assert first.equals(second)
    assert clean_df.equals(snapshot)
    assert not corrupt_clean_dataframe(clean_df, settings.paths.corruption_log, seed=7).equals(first)
