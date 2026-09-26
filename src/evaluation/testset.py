from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace, write_json

TEST_SET_SIZE = 10
QUESTION_TYPES = ("summary", "authors", "date", "categories")
QUESTION_TEMPLATES = {
    "summary": "What is the summary of the paper '{title}'?",
    "authors": "Who authored the paper '{title}'?",
    "date": "When was the paper '{title}' published?",
    "categories": "What categories does the paper '{title}' belong to?",
}


def _text(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(normalize_whitespace(str(item)) for item in value if item)
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return ""
    return normalize_whitespace(str(value))


def _ground_truth(row: pd.Series, question_type: str) -> str:
    if question_type == "summary":
        return first_sentence(_text(row.get("summary")))
    if question_type == "authors":
        return _text(row.get("authors_joined")) or _text(row.get("authors"))
    if question_type == "date":
        return _text(row.get("published"))[:10]
    return _text(row.get("categories_joined")) or _text(row.get("categories"))


def _pick_question(
    papers: pd.DataFrame,
    candidate_order: list[int],
    used: set[int],
    question_types: list[str],
    position: int,
) -> dict[str, Any] | None:
    for question_type in question_types:
        for index in candidate_order:
            if index in used:
                continue
            row = papers.iloc[index]
            ground_truth = _ground_truth(row, question_type)
            if not ground_truth:
                continue
            used.add(index)
            return {
                "id": f"eval_{position + 1:03d}",
                "question_type": question_type,
                "question": QUESTION_TEMPLATES[question_type].format(title=_text(row["title"])),
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [_text(row["paper_id"])],
            }
    return None


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Tao bo evaluation set tu cleaned dataframe.

    Pseudo-code:
    1. Kiem tra so luong document toi thieu.
    2. Chon mot so paper dai dien.
    3. Tao nhieu loai cau hoi:
       - summary
       - authors
       - date
       - categories
    4. Moi row can co:
       - id
       - question_type
       - question
       - ground_truth
       - ground_truth_doc_ids
    5. Ghi file JSON vao output_path.

    Cac dang cau hoi duoc xoay vong (3 summary, 3 authors, 2 date, 2 categories),
    moi cau hoi dung mot paper khac nhau de retrieval hit rate co y nghia.
    """
    papers = (
        df.dropna(subset=["paper_id", "title"])
        .drop_duplicates(subset="paper_id")
        .sort_values("paper_id")
        .reset_index(drop=True)
    )
    if len(papers) < TEST_SET_SIZE:
        raise ValueError(f"Need at least {TEST_SET_SIZE} unique papers to build the test set, got {len(papers)}.")

    # Rai deu cac paper duoc chon tren toan bo corpus (deterministic).
    step = len(papers) / TEST_SET_SIZE
    candidate_order = [int(i * step) for i in range(TEST_SET_SIZE)]
    candidate_order += [i for i in range(len(papers)) if i not in candidate_order]

    used: set[int] = set()
    test_set: list[dict[str, Any]] = []
    for position in range(TEST_SET_SIZE):
        preferred = QUESTION_TYPES[position % len(QUESTION_TYPES)]
        # Neu khong con paper nao co du lieu cho dang uu tien (vd Crossref khong tra `subject`),
        # chuyen sang dang tiep theo thay vi fail ca bo test.
        fallback_types = [preferred] + [t for t in QUESTION_TYPES if t != preferred]
        item = _pick_question(papers, candidate_order, used, fallback_types, position)
        if item is None:
            raise ValueError("Not enough papers with usable fields to build the test set.")
        if item["question_type"] != preferred:
            print(f"[testset] no paper has '{preferred}' data; using '{item['question_type']}' for {item['id']}")
        test_set.append(item)

    write_json(output_path, test_set)
    return test_set
