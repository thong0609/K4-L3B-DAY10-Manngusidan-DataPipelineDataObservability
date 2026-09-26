from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import ensure_parent, write_json
from ingestion.cleaning import _build_embedding_text


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path | str) -> pd.DataFrame:
    """Simulate 6 synthetic data corruption scenarios and log all modifications.

    1. Drop latest records: remove 20% newest papers.
    2. Blank summary: clear summary of selected rows.
    3. Inject noise: append gibberish noise to summaries.
    4. Truncate title: cut title to < 8 characters.
    5. Stale date: shift publication date to distant past (violating Freshness SLA).
    6. Duplicate rows: duplicate existing rows to violate uniqueness constraint.
    """
    target_log = Path(output_log_path)
    corrupted = df.copy()
    original_count = len(corrupted)
    log_actions: list[dict[str, Any]] = []

    # 1. Drop latest records (20%)
    drop_count = max(1, int(len(corrupted) * 0.20))
    corrupted = corrupted.sort_values(by="published", ascending=False).reset_index(drop=True)
    dropped_ids = corrupted.iloc[:drop_count]["paper_id"].tolist()
    corrupted = corrupted.iloc[drop_count:].reset_index(drop=True)
    log_actions.append({
        "type": "drop_latest_records",
        "dropped_count": drop_count,
        "dropped_paper_ids": dropped_ids,
        "description": "Dropped 20% most recent papers based on publication date",
    })

    # 2. Blank summary
    blank_idx = [0, 1] if len(corrupted) >= 2 else [0]
    blank_ids = corrupted.loc[blank_idx, "paper_id"].tolist()
    corrupted.loc[blank_idx, "summary"] = ""
    corrupted.loc[blank_idx, "summary_chars"] = 0
    log_actions.append({
        "type": "blank_summary",
        "affected_count": len(blank_idx),
        "affected_paper_ids": blank_ids,
        "description": "Erased paper summary to empty string (triggering min length violation)",
    })

    # 3. Inject noise
    noise_idx = [2, 3] if len(corrupted) >= 4 else []
    if noise_idx:
        noise_ids = corrupted.loc[noise_idx, "paper_id"].tolist()
        noise_text = " [CORRUPTED_NOISE_$$$#@!]" * 8
        corrupted.loc[noise_idx, "summary"] = corrupted.loc[noise_idx, "summary"] + noise_text
        corrupted.loc[noise_idx, "summary_chars"] = corrupted.loc[noise_idx, "summary"].str.len()
        log_actions.append({
            "type": "inject_noise",
            "affected_count": len(noise_idx),
            "affected_paper_ids": noise_ids,
            "description": "Injected gibberish noise tokens into summary",
        })

    # 4. Truncate title (< 8 characters)
    trunc_idx = [4, 5] if len(corrupted) >= 6 else []
    if trunc_idx:
        trunc_ids = corrupted.loc[trunc_idx, "paper_id"].tolist()
        corrupted.loc[trunc_idx, "title"] = "Bad"
        log_actions.append({
            "type": "truncate_title",
            "affected_count": len(trunc_idx),
            "affected_paper_ids": trunc_ids,
            "description": "Truncated title to 3 characters ('Bad')",
        })

    # 5. Stale date (shift published to 2010, age_days > 5000 for > 25% of dataset)
    stale_count = max(4, int(len(corrupted) * 0.35))
    stale_idx = list(range(6, min(len(corrupted), 6 + stale_count)))
    if stale_idx:
        stale_ids = corrupted.loc[stale_idx, "paper_id"].tolist()
        corrupted.loc[stale_idx, "published"] = "2010-01-01"
        corrupted.loc[stale_idx, "age_days"] = 5500
        log_actions.append({
            "type": "stale_date",
            "affected_count": len(stale_idx),
            "affected_paper_ids": stale_ids,
            "description": "Shifted publication date to 2010-01-01 (> 5000 days stale, violating Freshness SLA)",
        })

    # 6. Duplicate rows
    dup_rows = corrupted.iloc[:3].copy()
    corrupted = pd.concat([corrupted, dup_rows], ignore_index=True)
    log_actions.append({
        "type": "duplicate_rows",
        "duplicated_count": len(dup_rows),
        "duplicated_paper_ids": dup_rows["paper_id"].tolist(),
        "description": "Duplicated 3 rows to violate unique constraint on paper_id",
    })

    # 7. Rebuild text_for_embedding
    corrupted["text_for_embedding"] = corrupted.apply(_build_embedding_text, axis=1)

    # 8. Save corruption log
    log_payload = {
        "original_rows": original_count,
        "corrupted_rows": len(corrupted),
        "corruption_count": len(log_actions),
        "actions": log_actions,
    }
    ensure_parent(target_log)
    write_json(target_log, log_payload)

    return corrupted
