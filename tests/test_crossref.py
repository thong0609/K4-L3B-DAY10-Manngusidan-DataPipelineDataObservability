from __future__ import annotations

from dataclasses import asdict

import pytest
import requests

from core.utils import read_json, write_json
import ingestion.crossref as crossref
from ingestion.crossref import fetch_source_records, load_raw_records, parse_crossref_payload


def _item(**overrides):
    item = {
        "DOI": "10.1000/ABC",
        "title": ["  A   Title  "],
        "abstract": "<jats:p>Some &amp; abstract   text.</jats:p>",
        "author": [{"given": "Ada", "family": "Lovelace"}, {"name": "Consortium X"}, {}],
        "subject": ["AI", ""],
        "published": {"date-parts": [[2026, 5, 1]]},
        "indexed": {"date-time": "2026-06-02T10:00:00Z"},
        "URL": "https://doi.org/10.1000/abc",
        "link": [{"content-type": "application/pdf", "URL": "https://x/paper.pdf"}],
    }
    item.update(overrides)
    return item


def test_parse_snapshot_extracts_24_clean_records(records):
    assert len(records) == 24
    assert all(record.paper_id == record.paper_id.lower() for record in records)
    assert not any("<jats" in record.summary for record in records)
    assert all(record.categories for record in records)


def test_parse_normalizes_fields():
    [record] = parse_crossref_payload({"message": {"items": [_item()]}})
    assert record.paper_id == "10.1000/abc"
    assert record.title == "A Title"
    assert record.summary == "Some & abstract text."
    assert record.authors == ["Ada Lovelace", "Consortium X"]
    assert record.categories == ["AI"] and record.primary_category == "AI"
    assert record.published == "2026-05-01" and record.updated == "2026-06-02"
    assert record.pdf_url == "https://x/paper.pdf"


@pytest.mark.parametrize(
    "overrides",
    [{"DOI": ""}, {"title": []}, {"abstract": None}, {"published": None, "created": None}],
)
def test_parse_skips_invalid_items(overrides):
    assert parse_crossref_payload({"message": {"items": [_item(**overrides)]}}) == []


def test_parse_dedups_and_pads_partial_dates():
    items = [
        _item(published={"date-parts": [[2025]]}, link=[], indexed=None, deposited=None, created=None),
        _item(),
    ]
    [record] = parse_crossref_payload({"message": {"items": items}})
    assert record.published == "2025-01-01"
    assert record.updated == "2025-01-01"
    assert record.pdf_url == record.abs_url


def test_parse_handles_empty_payload():
    assert parse_crossref_payload({}) == []


def test_fetch_uses_snapshot_by_default(settings):
    records = fetch_source_records(settings)
    assert len(records) == 24
    assert len(read_json(settings.paths.raw_records_json)) == 24


def test_load_raw_records_roundtrip(settings, records):
    loaded = load_raw_records(settings.paths.raw_records_json)
    assert [asdict(r) for r in loaded] == [asdict(r) for r in records]


class _Response:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))

    def json(self):
        return self._payload


def test_fetch_refresh_calls_api_and_saves_raw(settings, monkeypatch):
    from dataclasses import replace

    payload = {"message": {"items": [_item()]}}
    calls = []
    monkeypatch.setattr(crossref.requests, "get", lambda *a, **k: calls.append(k) or _Response(200, payload))
    records = fetch_source_records(replace(settings, refresh_source=True))
    assert [r.paper_id for r in records] == ["10.1000/abc"]
    assert calls[0]["params"]["rows"] == settings.max_results
    assert read_json(settings.paths.raw_api_response) == payload


def test_fetch_falls_back_to_snapshot_on_429(settings, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(crossref.time, "sleep", lambda _: None)
    monkeypatch.setattr(crossref.requests, "get", lambda *a, **k: _Response(429))
    records = fetch_source_records(replace(settings, refresh_source=True))
    assert len(records) == 24  # snapshot mau, khong bi ghi de


def test_fetch_without_snapshot_raises(settings, monkeypatch):
    monkeypatch.setattr(crossref.time, "sleep", lambda _: None)
    settings.paths.raw_api_response.unlink()
    with pytest.raises(RuntimeError, match="no snapshot"):
        fetch_source_records(settings)


def test_fetch_rejects_empty_api_result(settings, monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(crossref.requests, "get", lambda *a, **k: _Response(200, {"message": {"items": []}}))
    snapshot_before = read_json(settings.paths.raw_api_response)
    records = fetch_source_records(replace(settings, refresh_source=True))
    assert len(records) == 24
    assert read_json(settings.paths.raw_api_response) == snapshot_before
    write_json(settings.paths.raw_api_response, snapshot_before)
