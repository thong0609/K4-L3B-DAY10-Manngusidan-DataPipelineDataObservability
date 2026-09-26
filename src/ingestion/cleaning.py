from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord

CLEAN_COLUMNS = [
    "paper_id",
    "title",
    "summary",
    "authors",
    "categories",
    "primary_category",
    "published",
    "updated",
    "abs_url",
    "pdf_url",
    "comment",
    "age_days",
    "authors_joined",
    "categories_joined",
    "summary_chars",
    "text_for_embedding",
]


def _clean_list(values) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned: list[str] = []
    for value in values:
        item = normalize_whitespace(str(value)) if value is not None else ""
        if item and item not in cleaned:
            cleaned.append(item)
    return cleaned


def _clean_str(value) -> str:
    return normalize_whitespace(str(value)) if value is not None and not pd.isna(value) else ""


def _build_embedding_text(row: pd.Series) -> str:
    return "\n".join(
        [
            f"Title: {row['title']}",
            f"Authors: {row['authors_joined']}",
            f"Published: {row['published']}",
            f"Categories: {row['categories_joined']}",
            f"Summary: {row['summary']}",
        ]
    )


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """TODO(student): clean raw records thanh dataframe san sang de embed.

    Pseudo-code:
    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Tinh age_days.
    4. Tao cot helper:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding
    5. Drop duplicates va filter row xau.
    6. Sort dataframe va return.
    """
    if not records:
        return pd.DataFrame(columns=CLEAN_COLUMNS)

    df = pd.DataFrame([asdict(record) for record in records])

    # 1. Normalize text + list fields.
    for column in ("paper_id", "title", "summary", "primary_category", "abs_url", "pdf_url", "comment"):
        df[column] = df[column].map(_clean_str)
    df["paper_id"] = df["paper_id"].str.lower()
    df["authors"] = df["authors"].map(_clean_list)
    df["categories"] = df["categories"].map(_clean_list)
    df["primary_category"] = [
        primary or (categories[0] if categories else "")
        for primary, categories in zip(df["primary_category"], df["categories"])
    ]

    # 2. Parse dates (invalid -> NaT, dropped below); `updated` falls back to `published`.
    published = pd.to_datetime(df["published"], errors="coerce", utc=True)
    updated = pd.to_datetime(df["updated"], errors="coerce", utc=True).fillna(published)

    # 3. age_days = (run_date - published).days
    run_ts = pd.Timestamp(run_date if run_date.tzinfo else run_date.replace(tzinfo=UTC)).tz_convert("UTC")
    df["age_days"] = (run_ts.normalize() - published.dt.normalize()).dt.days
    df["published"] = published.dt.strftime("%Y-%m-%d")
    df["updated"] = updated.dt.strftime("%Y-%m-%d")

    # 5. Filter bad rows before building helper text.
    valid = (
        published.notna()
        & df["paper_id"].ne("")
        & df["title"].ne("")
        & df["summary"].ne("")
    )
    df = df[valid].copy()

    # 4. Helper columns.
    df["age_days"] = df["age_days"].astype(int)
    df["authors_joined"] = df["authors"].map(compact_join)
    df["categories_joined"] = df["categories"].map(compact_join)
    df["summary_chars"] = df["summary"].str.len().astype(int)
    df["text_for_embedding"] = df.apply(_build_embedding_text, axis=1)

    # 5-6. Deduplicate on paper_id (keep most recently updated) and sort.
    df = (
        df.sort_values(["paper_id", "updated"], ascending=[True, False])
        .drop_duplicates(subset="paper_id", keep="first")
        .sort_values(["published", "paper_id"], ascending=[False, True])
        .reset_index(drop=True)
    )
    return df[CLEAN_COLUMNS]
