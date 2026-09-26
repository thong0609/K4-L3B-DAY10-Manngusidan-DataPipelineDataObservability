from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from core.utils import now_utc, write_json
from ingestion.cleaning import _build_embedding_text

SEED = 42
DROP_LATEST_RATIO = 0.20
BLANK_SUMMARY_RATIO = 0.15
NOISE_RATIO = 0.15
TRUNCATE_TITLE_RATIO = 0.15
# > 25% de freshness SLA (MAX_STALE_RATIO) chac chan bi vi pham.
STALE_DATE_RATIO = 0.35
DUPLICATE_RATIO = 0.15
TRUNCATED_TITLE_CHARS = 7
STALE_SHIFT_DAYS = 365
NOISE_TOKENS = "#### @@@ lorem ipsum �� 0xDEADBEEF <div>null</div> ~~~ %%%"


def _count(total: int, ratio: float) -> int:
    return max(1, math.ceil(total * ratio)) if total else 0


def _event(kind: str, row: pd.Series, field: str | None, before: Any, after: Any) -> dict[str, Any]:
    return {
        "corruption": kind,
        "paper_id": row["paper_id"],
        "field": field,
        "before": before,
        "after": after,
    }


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path, seed: int = SEED) -> pd.DataFrame:
    """Simulate 6 dang data corruption tren clean dataframe (deterministic theo `seed`).

    Pseudo-code:
    1. Drop mot so latest records.
    2. Blank summary o mot so dong.
    3. Inject noise vao text.
    4. Lam title bi truncate.
    5. Lam published date cu di.
    6. Add duplicate rows.
    7. Rebuild `text_for_embedding`.
    8. Ghi corruption log vao output_log_path.

    Cac buoc 2-5 dung cac tap dong rieng biet de moi loi co the truy vet doc lap trong log.
    """
    rng = np.random.default_rng(seed)
    events: list[dict[str, Any]] = []
    corrupted = df.copy().reset_index(drop=True)
    input_rows = len(corrupted)

    # 1. Drop 20% bai bao moi nhat (mo phong ingestion bi tre / mat batch moi).
    n_drop = _count(input_rows, DROP_LATEST_RATIO)
    latest = corrupted.sort_values(["published", "paper_id"], ascending=[False, True]).head(n_drop)
    for _, row in latest.iterrows():
        events.append(_event("drop_latest_records", row, None, row["published"], "<dropped>"))
    corrupted = corrupted.drop(index=latest.index).reset_index(drop=True)

    # Chia cac dong con lai thanh cac tap rieng cho buoc 2-5.
    total = len(corrupted)
    order = list(rng.permutation(total))
    plan = [
        ("blank_summary", BLANK_SUMMARY_RATIO),
        ("inject_noise", NOISE_RATIO),
        ("truncate_title", TRUNCATE_TITLE_RATIO),
        ("stale_date", STALE_DATE_RATIO),
    ]
    targets: dict[str, list[int]] = {}
    for kind, ratio in plan:
        size = min(_count(total, ratio), len(order))
        targets[kind], order = order[:size], order[size:]

    # 2. Blank summary.
    for idx in targets["blank_summary"]:
        row = corrupted.loc[idx]
        events.append(_event("blank_summary", row, "summary", row["summary"], ""))
        corrupted.at[idx, "summary"] = ""

    # 3. Inject noise vao giua summary.
    for idx in targets["inject_noise"]:
        row = corrupted.loc[idx]
        words = str(row["summary"]).split()
        cut = len(words) // 2
        noisy = " ".join(words[:cut] + [NOISE_TOKENS] + words[cut:] + [NOISE_TOKENS])
        events.append(_event("inject_noise", row, "summary", row["summary"], noisy))
        corrupted.at[idx, "summary"] = noisy

    # 4. Truncate title xuong < 8 ky tu.
    for idx in targets["truncate_title"]:
        row = corrupted.loc[idx]
        short = str(row["title"])[:TRUNCATED_TITLE_CHARS].rstrip()
        events.append(_event("truncate_title", row, "title", row["title"], short))
        corrupted.at[idx, "title"] = short

    # 5. Lui published date ve 365 ngay truoc.
    for idx in targets["stale_date"]:
        row = corrupted.loc[idx]
        old = pd.Timestamp(row["published"]) - pd.Timedelta(days=STALE_SHIFT_DAYS)
        stale = old.strftime("%Y-%m-%d")
        events.append(_event("stale_date", row, "published", row["published"], stale))
        corrupted.at[idx, "published"] = stale
        corrupted.at[idx, "age_days"] = int(row["age_days"]) + STALE_SHIFT_DAYS

    # 6. Nhan doi mot so dong (sau khi da bi lam ban) de tao trung lap paper_id.
    n_dup = _count(total, DUPLICATE_RATIO)
    dup_idx = sorted(rng.choice(total, size=min(n_dup, total), replace=False).tolist())
    duplicates = corrupted.loc[dup_idx]
    for _, row in duplicates.iterrows():
        events.append(_event("duplicate_rows", row, "paper_id", None, row["paper_id"]))
    corrupted = pd.concat([corrupted, duplicates], ignore_index=True)

    # 7. Rebuild cac cot phu thuoc de embedding phan anh dung du lieu ban.
    corrupted["summary_chars"] = corrupted["summary"].astype(str).str.len()
    corrupted["text_for_embedding"] = corrupted.apply(_build_embedding_text, axis=1)

    # 8. Corruption log.
    summary: dict[str, int] = {}
    for event in events:
        summary[event["corruption"]] = summary.get(event["corruption"], 0) + 1
    write_json(
        output_log_path,
        {
            "generated_at": now_utc().isoformat(),
            "seed": seed,
            "input_rows": input_rows,
            "output_rows": len(corrupted),
            "corruption_counts": summary,
            "affected_paper_ids": sorted({event["paper_id"] for event in events}),
            "events": events,
        },
    )
    return corrupted
