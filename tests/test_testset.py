from __future__ import annotations

from collections import Counter

import pytest

from core.utils import read_json
from evaluation.testset import QUESTION_TEMPLATES, build_test_set


def test_builds_ten_balanced_questions(clean_df, settings):
    test_set = build_test_set(clean_df, settings.paths.eval_testset)
    assert len(test_set) == 10
    assert Counter(item["question_type"] for item in test_set) == {
        "summary": 3, "authors": 3, "date": 2, "categories": 2,
    }
    doc_ids = [item["ground_truth_doc_ids"][0] for item in test_set]
    assert len(set(doc_ids)) == 10 and set(doc_ids) <= set(clean_df["paper_id"])
    assert read_json(settings.paths.eval_testset) == test_set


def test_is_deterministic(clean_df, settings):
    first = build_test_set(clean_df, settings.paths.eval_testset)
    second = build_test_set(clean_df.sample(frac=1, random_state=1), settings.paths.eval_testset)
    assert first == second


def test_templates_match_qa_routing_keywords():
    assert "who authored" in QUESTION_TEMPLATES["authors"].lower()
    assert "when was" in QUESTION_TEMPLATES["date"].lower()
    assert "what categories" in QUESTION_TEMPLATES["categories"].lower()


def test_falls_back_when_categories_missing(clean_df, settings, capsys):
    no_categories = clean_df.assign(categories=[[] for _ in range(len(clean_df))], categories_joined="")
    test_set = build_test_set(no_categories, settings.paths.eval_testset)
    assert len(test_set) == 10
    assert "categories" not in {item["question_type"] for item in test_set}
    assert "no paper has 'categories' data" in capsys.readouterr().out


def test_requires_ten_papers(clean_df, settings):
    with pytest.raises(ValueError, match="at least 10"):
        build_test_set(clean_df.head(5), settings.paths.eval_testset)


def test_raises_when_papers_have_no_usable_fields(clean_df, settings):
    empty = clean_df.assign(summary="", authors_joined="", authors=[[] for _ in range(len(clean_df))],
                            categories_joined="", categories=[[] for _ in range(len(clean_df))], published="")
    with pytest.raises(ValueError, match="usable fields"):
        build_test_set(empty, settings.paths.eval_testset)
