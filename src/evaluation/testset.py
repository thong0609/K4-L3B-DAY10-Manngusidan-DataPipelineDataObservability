from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import ensure_parent, first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path: Path | str) -> list[dict[str, Any]]:
    """Build standardized evaluation test set with 10 questions across 4 categories."""
    target_path = Path(output_path)
    if len(df) < 10:
        raise ValueError(f"Need at least 10 documents to build benchmark, got {len(df)}")

    rows = df.iloc[:10].to_dict(orient="records")
    test_set: list[dict[str, Any]] = []

    type_assignments = [
        "summary", "summary", "summary",
        "authors", "authors", "authors",
        "date", "date",
        "categories", "categories",
    ]

    for index, (row, q_type) in enumerate(zip(rows, type_assignments)):
        title = row["title"]
        paper_id = row["paper_id"]

        if q_type == "summary":
            question = f"What is the summary of the paper '{title}'?"
            ground_truth = first_sentence(row["summary"])
        elif q_type == "authors":
            question = f"Who authored the paper '{title}'?"
            ground_truth = row["authors_joined"]
        elif q_type == "date":
            question = f"When was the paper '{title}' published?"
            ground_truth = row["published"]
        elif q_type == "categories":
            question = f"What categories does the paper '{title}' belong to?"
            ground_truth = row["categories_joined"]
        else:
            question = f"What is the summary of the paper '{title}'?"
            ground_truth = first_sentence(row["summary"])

        test_set.append(
            {
                "id": f"eval-{index + 1:02d}",
                "question_type": q_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [paper_id],
            }
        )

    ensure_parent(target_path)
    write_json(target_path, test_set)
    return test_set
