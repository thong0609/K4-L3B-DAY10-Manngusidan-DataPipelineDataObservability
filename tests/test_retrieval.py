from __future__ import annotations

from dataclasses import replace

import pytest

from core.config import normalized_provider, require_llm_credentials
from core.utils import read_json
from evaluation.testset import build_test_set
from retrieval.index import LocalEmbeddingIndex
from retrieval.llm import build_llm
from retrieval.qa import answer_question


@pytest.fixture
def index(clean_df, settings):
    return LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)


def test_build_persists_collection_and_manifest(index, settings):
    manifest = read_json(settings.paths.embeddings_json)
    assert manifest["collection_name"] == settings.baseline_collection_name
    assert len(manifest["documents"]) == 24 == index.collection.count()
    reloaded = LocalEmbeddingIndex.load(settings)
    assert reloaded.collection.count() == 24


def test_collection_names_per_state(settings, tmp_path):
    derive = LocalEmbeddingIndex._derive_collection_name
    assert derive(settings, None) == settings.baseline_collection_name
    assert derive(settings, settings.paths.corrupted_embeddings_json) == settings.corrupted_collection_name
    assert derive(settings, settings.paths.repaired_embeddings_json) == settings.repaired_collection_name
    assert derive(settings, tmp_path / "Custom Index.json") == "custom-index"


def test_semantic_search_and_lookup(index, clean_df):
    row = clean_df.iloc[0]
    results = index.search(row["title"], top_k=3)
    # Semantic search thuan co the xep paper tuong tu len dau; qa.py vi vay uu tien exact-title lookup.
    assert row["paper_id"] in [r.paper_id for r in results]
    assert all(0 < r.score <= 1 for r in results)
    assert results == sorted(results, key=lambda r: r.score, reverse=True)
    assert index.lookup(row["title"].upper())["paper_id"] == row["paper_id"]
    assert index.lookup(row["paper_id"])["title"] == row["title"]
    assert index.lookup("does not exist") is None


def test_answer_question_routes_by_type(index, clean_df, settings):
    test_set = build_test_set(clean_df, settings.paths.eval_testset)
    for item in test_set:
        result = answer_question(item["question"], settings, index)
        assert result.retrieved_doc_ids[0] == item["ground_truth_doc_ids"][0]
        assert result.answer == item["ground_truth"]
    free_text = answer_question("agentic retrieval for knowledge tasks", settings, index, top_k=2)
    assert len(free_text.retrieved_doc_ids) == 2


def test_build_llm_providers(settings):
    assert build_llm(settings).invoke("hi").content
    fake = {"google_api_key": "k", "openai_api_key": "k", "anthropic_api_key": "k",
            "openrouter_api_key": "k", "custom_llm_base_url": "http://localhost:1/v1"}
    for provider in ("gemini", "openai", "anthropic", "openrouter", "ollama", "custom", "Custom LLM"):
        cfg = replace(settings, llm_provider=provider, model_name="m", **fake)
        assert build_llm(cfg) is not None


def test_credentials_are_required(settings):
    assert normalized_provider(replace(settings, llm_provider="Anthorpic")) == "anthropic"
    for provider in ("gemini", "openai", "anthropic", "openrouter", "custom"):
        with pytest.raises(RuntimeError, match="required"):
            require_llm_credentials(replace(settings, llm_provider=provider, google_api_key=None,
                                            openai_api_key=None, anthropic_api_key=None,
                                            openrouter_api_key=None, custom_llm_base_url=None))
    with pytest.raises(RuntimeError, match="Unsupported"):
        require_llm_credentials(replace(settings, llm_provider="nope"))
