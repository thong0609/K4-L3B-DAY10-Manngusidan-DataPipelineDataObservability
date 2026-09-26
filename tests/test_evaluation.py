from __future__ import annotations

import sys
import types

import pandas as pd
import pytest

from evaluation import metrics
from evaluation.metrics import JudgeVerdict, _judge_answer, _run_ragas, _token_f1, evaluate_pipeline
from evaluation.testset import build_test_set
from retrieval.index import LocalEmbeddingIndex


def test_token_f1():
    assert _token_f1("a b c", "a b c") == 1.0
    assert _token_f1("a b", "c d") == 0.0
    assert _token_f1("", "x") == 0.0
    assert 0 < _token_f1("a b c d", "a b") < 1


def test_judge_falls_back_to_heuristic_without_llm(settings):
    verdict = _judge_answer(settings, "q", "exact answer", "exact answer")
    assert verdict.score == 5 and verdict.correct and "Fallback" in verdict.reasoning
    assert _judge_answer(settings, "q", "one two", "one three").score == 3
    assert _judge_answer(settings, "q", "one", "zzz").correct is False


def test_judge_uses_structured_llm_when_available(settings, monkeypatch):
    class _Structured:
        def invoke(self, prompt):
            return JudgeVerdict(score=4, correct=True, reasoning="llm")

    class _Llm:
        def with_structured_output(self, schema):
            return _Structured()

    monkeypatch.setattr(metrics, "build_llm", lambda **kwargs: _Llm())
    assert _judge_answer(settings, "q", "a", "b").reasoning == "llm"


def test_ragas_skipped_by_default(settings):
    assert "skipped" in _run_ragas(settings, [])


def test_ragas_summary_from_fake_module(settings, monkeypatch):
    class _Result:
        def to_pandas(self):
            return pd.DataFrame({"faithfulness": [1.0, float("nan")], "answer_relevancy": [float("nan")] * 2,
                                 "context_precision": [0.5, 1.0], "context_recall": [1.0, 1.0]})

    fake_ragas = types.ModuleType("ragas")
    fake_ragas.evaluate = lambda dataset, **kwargs: _Result()
    fake_ragas.RunConfig = lambda **kwargs: kwargs
    fake_metrics = types.ModuleType("ragas.metrics")
    for name in ("answer_relevancy", "context_precision", "context_recall", "faithfulness"):
        setattr(fake_metrics, name, types.SimpleNamespace(name=name))
    monkeypatch.setitem(sys.modules, "ragas", fake_ragas)
    monkeypatch.setitem(sys.modules, "ragas.metrics", fake_metrics)
    monkeypatch.setattr(metrics, "MiniLMEmbeddings", lambda name: object())
    monkeypatch.setenv("RUN_RAGAS", "1")
    answers = [{"question": "q", "answer": "a", "ground_truth": "a", "retrieved_contexts": ["c"]}] * 2
    summary = _run_ragas(settings, answers)
    assert summary["faithfulness"] == 1.0 and summary["faithfulness_failed_samples"] == 1
    assert summary["answer_relevancy"] is None and summary["context_precision"] == 0.75


def test_ragas_errors_are_reported(settings, monkeypatch):
    fake_ragas = types.ModuleType("ragas")

    def boom(*args, **kwargs):
        raise KeyError(0)

    fake_ragas.evaluate, fake_ragas.RunConfig = boom, (lambda **kwargs: kwargs)
    fake_metrics = types.ModuleType("ragas.metrics")
    for name in ("answer_relevancy", "context_precision", "context_recall", "faithfulness"):
        setattr(fake_metrics, name, types.SimpleNamespace(name=name))
    monkeypatch.setitem(sys.modules, "ragas", fake_ragas)
    monkeypatch.setitem(sys.modules, "ragas.metrics", fake_metrics)
    monkeypatch.setattr(metrics, "MiniLMEmbeddings", lambda name: object())
    monkeypatch.setenv("RUN_RAGAS", "1")
    answers = [{"question": "q", "answer": "a", "ground_truth": "a", "retrieved_contexts": ["c"]}]
    assert "error" in _run_ragas(settings, answers)


@pytest.mark.parametrize("paths", [("metrics_output", "answers_output")])
def test_evaluate_pipeline_on_clean_index(clean_df, settings, tmp_path, paths):
    build_test_set(clean_df, settings.paths.eval_testset)
    index = LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)
    bundle = evaluate_pipeline(settings, index, settings.paths.eval_testset,
                               tmp_path / "metrics.json", tmp_path / "answers.json")
    assert bundle.summary["samples"] == 10
    assert bundle.summary["retrieval_hit_rate"] == 1.0 and bundle.summary["mean_token_f1"] == 1.0
    assert (tmp_path / "answers.json").exists()
