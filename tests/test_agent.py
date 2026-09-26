from __future__ import annotations

from types import SimpleNamespace

import retrieval.agent as agent_module
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex


def test_agent_tools_query_the_index(clean_df, settings, monkeypatch):
    captured = {}

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return "agent"

    monkeypatch.setattr(agent_module, "create_agent", fake_create_agent)
    index = LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)
    assert build_agent(settings, index) == "agent"

    tools = {tool.name: tool for tool in captured["tools"]}
    row = clean_df.iloc[0]
    search_output = tools["semantic_search_papers"].invoke({"query": row["title"], "top_k": 2})
    assert f"paper_id: {row['paper_id']}" in search_output
    assert row["title"] in tools["lookup_paper"].invoke({"paper_id_or_title": row["paper_id"]})
    assert tools["lookup_paper"].invoke({"paper_id_or_title": "unknown"}) == "No exact paper match found."
    assert "Crossref" in captured["system_prompt"]


def test_run_agent_question_returns_final_message():
    class _Agent:
        def __init__(self, messages):
            self.messages = messages

        def invoke(self, payload):
            return {"messages": self.messages}

    assert run_agent_question(_Agent([SimpleNamespace(content="final answer")]), "q") == "final answer"
    assert run_agent_question(_Agent([]), "q") == ""
