from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import shutil

import pandas as pd
import pytest
import requests

from core.config import Settings, load_settings
from core.utils import read_json
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import PaperRecord, parse_crossref_payload

REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = REPO_ROOT / "data" / "raw" / "crossref_response.json"
# Ngay chay co dinh de age_days/freshness khong phu thuoc vao ngay chay test.
FROZEN_NOW = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch):
    """Khong dung API key that, khong goi mang, khong bat Ragas trong test."""
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("LLM_MODEL", "mock")
    for name in ("REFRESH_SOURCE", "REFRESH_TEST_SET", "RUN_RAGAS"):
        monkeypatch.delenv(name, raising=False)

    def _no_network(*args, **kwargs):
        raise requests.ConnectionError("network disabled in tests")

    monkeypatch.setattr(requests, "get", _no_network)


@pytest.fixture
def frozen_now(monkeypatch):
    import ingestion.corruption
    import observability.self_healing
    import pipelines.phase1

    for module in (pipelines.phase1, observability.self_healing, ingestion.corruption):
        monkeypatch.setattr(module, "now_utc", lambda: FROZEN_NOW)
    return FROZEN_NOW


@pytest.fixture
def settings(tmp_path) -> Settings:
    """Project tam trong tmp_path, co san raw snapshot mau (lineage anchor)."""
    raw_dir = tmp_path / "project" / "data" / "raw"
    raw_dir.mkdir(parents=True)
    shutil.copy(SNAPSHOT, raw_dir / "crossref_response.json")
    loaded = load_settings(tmp_path / "project")
    records = parse_crossref_payload(read_json(SNAPSHOT))
    from dataclasses import asdict

    from core.utils import write_json

    write_json(loaded.paths.raw_records_json, [asdict(record) for record in records])
    return loaded


@pytest.fixture(scope="session")
def payload() -> dict:
    return read_json(SNAPSHOT)


@pytest.fixture(scope="session")
def records(payload) -> list[PaperRecord]:
    return parse_crossref_payload(payload)


@pytest.fixture
def clean_df(records) -> pd.DataFrame:
    return build_clean_dataframe(records, FROZEN_NOW)
