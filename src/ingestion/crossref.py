from __future__ import annotations

from dataclasses import asdict, dataclass
import html
from pathlib import Path
import re
import time

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json

CROSSREF_WORKS_URL = "https://api.crossref.org/works"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3
_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_text(value: str | None) -> str:
    """Strip JATS/HTML tags (e.g. <jats:p>), unescape entities, collapse whitespace."""
    if not value:
        return ""
    return normalize_whitespace(html.unescape(_TAG_RE.sub(" ", value)))


def _first(values: list | None) -> str:
    return _clean_text(values[0]) if values else ""


def _date_from_parts(field: dict | None) -> str:
    """Convert Crossref {"date-parts": [[y, m, d]]} to ISO date, padding missing month/day with 1."""
    if not field:
        return ""
    parts = (field.get("date-parts") or [[]])[0]
    if not parts or parts[0] is None:
        return ""
    year, month, day = (list(parts) + [1, 1])[:3]
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _published_date(item: dict) -> str:
    for key in ("published", "published-online", "published-print", "issued", "created"):
        value = _date_from_parts(item.get(key))
        if value:
            return value
    return ""


def _updated_date(item: dict, fallback: str) -> str:
    for key in ("indexed", "deposited", "created"):
        date_time = (item.get(key) or {}).get("date-time")
        if date_time:
            return date_time[:10]
    return fallback


def _authors(item: dict) -> list[str]:
    names = []
    for author in item.get("author") or []:
        name = " ".join(part for part in (author.get("given"), author.get("family")) if part)
        name = _clean_text(name or author.get("name"))
        if name:
            names.append(name)
    return names


def _pdf_url(item: dict, default: str) -> str:
    for link in item.get("link") or []:
        if "pdf" in (link.get("content-type") or "").lower() and link.get("URL"):
            return link["URL"]
    return default


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord.

    Pseudo-code:
    1. Duyet `payload["message"]["items"]`.
    2. Lay DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuan hoa text va bo record khong hop le.
    4. Tra ve list `PaperRecord`.
    """
    records: list[PaperRecord] = []
    seen: set[str] = set()
    for item in (payload.get("message") or {}).get("items") or []:
        paper_id = (item.get("DOI") or "").strip().lower()
        title = _first(item.get("title"))
        summary = _clean_text(item.get("abstract"))
        published = _published_date(item)
        # Record khong co DOI/title/abstract/ngay xuat ban thi khong dung duoc cho RAG.
        if not (paper_id and title and summary and published) or paper_id in seen:
            continue
        seen.add(paper_id)

        categories = [c for c in (_clean_text(s) for s in item.get("subject") or []) if c]
        abs_url = item.get("URL") or f"https://doi.org/{paper_id}"
        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=_authors(item),
                categories=categories,
                primary_category=categories[0] if categories else "",
                published=published,
                updated=_updated_date(item, published),
                abs_url=abs_url,
                pdf_url=_pdf_url(item, abs_url),
                comment=f"Crossref record {paper_id}",
            )
        )
    return records


def _request_crossref(settings: Settings) -> dict:
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    headers = {"User-Agent": "day10-data-observability-lab/0.1 (mailto:lab@example.com)"}
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(CROSSREF_WORKS_URL, params=params, headers=headers, timeout=30)
            if response.status_code in RETRYABLE_STATUS:
                raise requests.HTTPError(f"Crossref returned {response.status_code}", response=response)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < MAX_ATTEMPTS:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Crossref request failed after {MAX_ATTEMPTS} attempts: {last_error}")


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi source API, luu raw response, parse thanh records.

    Pseudo-code:
    1. Tao params tu `settings.source_query`, `settings.source_filter`, `settings.max_results`.
    2. Goi API voi retry cho cac status code nhu 429/503.
    3. Luu raw response vao `settings.paths.raw_api_response`.
    4. Parse payload bang `parse_crossref_payload`.
    5. Luu records vao `settings.paths.raw_records_json`.

    Neu API loi (mat mang, 429, ...) hoac khong tra ve record hop le nao,
    fallback sang snapshot co san tai `settings.paths.raw_api_response`.
    """
    snapshot_path = settings.paths.raw_api_response
    try:
        payload = _request_crossref(settings)
        records = parse_crossref_payload(payload)
        if not records:
            raise RuntimeError("Crossref returned no valid records.")
        # Chi ghi de snapshot khi API tra ve du lieu dung duoc.
        write_json(snapshot_path, payload)
        print(f"[crossref] fetched {len(records)} records from API")
    except Exception as exc:
        if not snapshot_path.exists():
            raise RuntimeError(f"Crossref API failed and no snapshot at {snapshot_path}") from exc
        print(f"[crossref] API unavailable ({exc}); falling back to snapshot {snapshot_path}")
        payload = read_json(snapshot_path)
        records = parse_crossref_payload(payload)

    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh `PaperRecord`."""
    return [PaperRecord(**row) for row in read_json(path)]
