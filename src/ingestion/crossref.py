from __future__ import annotations

from dataclasses import asdict, dataclass
<<<<<<< HEAD
from html.parser import HTMLParser
import logging
=======
import html
>>>>>>> ndmnhat
from pathlib import Path
import re
import time

import requests

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.config import Settings
<<<<<<< HEAD
from core.utils import ensure_parent, normalize_whitespace, read_json, write_json


logger = logging.getLogger(__name__)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag, attrs) -> None:
        if tag.split(":")[-1] in {"p", "div", "br", "title"}:
            self.parts.append(" ")

    def handle_endtag(self, tag) -> None:
        self.handle_starttag(tag, [])


def _clean_text(value: str | None) -> str:
    parser = _TextExtractor()
    parser.feed(value or "")
    parser.close()
    return normalize_whitespace("".join(parser.parts))


def _date(item: dict, *fields: str) -> str:
    for field in fields:
        value = item.get(field) or {}
        parts = value.get("date-parts") or []
        if parts and parts[0]:
            # Preserve partial dates instead of inventing a month or day.
            return "-".join(
                f"{part:04d}" if index == 0 else f"{part:02d}"
                for index, part in enumerate(parts[0][:3])
            )
        if value.get("date-time"):
            return value["date-time"][:10]
    return ""
=======
from core.utils import normalize_whitespace, read_json, write_json

CROSSREF_WORKS_URL = "https://api.crossref.org/works"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3
_TAG_RE = re.compile(r"<[^>]+>")
>>>>>>> ndmnhat


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

    Cac buoc:
    1. Duyet `payload["message"]["items"]`.
    2. Lay DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuan hoa text va bo record khong hop le.
    4. Tra ve list `PaperRecord`.
    """
<<<<<<< HEAD
    items = payload["message"]["items"]
    if not isinstance(items, list):
        raise ValueError("Crossref message.items must be a list.")

    records = []
    for item in items:
        paper_id = (item.get("DOI") or "").strip().lower()
        titles = item.get("title") or []
        title = _clean_text(titles[0] if titles else "")
        if not paper_id or not title:
            continue

        authors = []
        for author in item.get("author") or []:
            name = " ".join(
                part for part in (author.get("given"), author.get("family")) if part
            )
            name = _clean_text(name or author.get("name"))
            if name:
                authors.append(name)
        categories = [
            text for subject in item.get("subject") or []
            if (text := _clean_text(subject))
        ]
        records.append(PaperRecord(
            paper_id=paper_id,
            title=title,
            summary=_clean_text(item.get("abstract")),
            authors=authors,
            categories=categories,
            primary_category=categories[0] if categories else "",
            published=_date(item, "published", "published-online", "published-print", "issued"),
            updated=_date(item, "deposited", "created"),
            abs_url=item.get("URL") or f"https://doi.org/{paper_id}",
            pdf_url=next((
                link["URL"] for link in item.get("link") or []
                if link.get("content-type") == "application/pdf" and link.get("URL")
            ), ""),
            comment=f"Crossref record {paper_id}",
        ))
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi API va luu raw artifacts; doc snapshot neu API/mang bi loi.
=======
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
>>>>>>> ndmnhat

    Cac buoc:
    1. Tao params tu `settings.source_query`, `settings.source_filter`, `settings.max_results`.
    2. Retry loi mang/5xx; fallback ngay khi 429 hoac sau khi retry that bai.
    3. Chi luu raw response hop le vao `settings.paths.raw_api_response`.
    4. Parse payload bang `parse_crossref_payload`.
    5. Luu records vao `settings.paths.raw_records_json`.

    Mac dinh dung lai snapshot co san (lineage anchor, ket qua tai lap duoc);
    chi goi API khi REFRESH_SOURCE=1 hoac chua co snapshot.
    Neu API loi (mat mang, 429, ...) hoac khong tra ve record hop le nao,
    fallback sang snapshot co san tai `settings.paths.raw_api_response`.
    """
<<<<<<< HEAD
    if not 1 <= settings.max_results <= 1000:
        raise ValueError("max_results must be between 1 and 1000.")

    retry = Retry(
        total=2,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"],
        # Switch immediately to offline on 429 rather than waiting out a quota.
        respect_retry_after_header=False,
    )
    try:
        with requests.Session() as session:
            session.mount("https://", HTTPAdapter(max_retries=retry))
            response = session.get(
                "https://api.crossref.org/works",
                params={
                    "query": settings.source_query,
                    "filter": settings.source_filter,
                    "rows": settings.max_results,
                },
                headers={"User-Agent": "Day10DataPipeline/1.0"},
                timeout=(5, 15),
            )
            response.raise_for_status()
            records = parse_crossref_payload(response.json())
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        logger.warning("Crossref unavailable (%s); loading offline snapshot: %s",
                       type(exc).__name__, settings.paths.raw_api_response)
        # Never replace the good snapshot with an error response.
        records = parse_crossref_payload(read_json(settings.paths.raw_api_response))
    else:
        ensure_parent(settings.paths.raw_api_response)
        settings.paths.raw_api_response.write_bytes(response.content)
=======
    snapshot_path = settings.paths.raw_api_response
    if not settings.refresh_source and snapshot_path.exists():
        records = parse_crossref_payload(read_json(snapshot_path))
        print(f"[crossref] loaded {len(records)} records from snapshot (set REFRESH_SOURCE=1 to call the API)")
        write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
        return records
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
>>>>>>> ndmnhat

    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh `PaperRecord`."""
<<<<<<< HEAD
    return [PaperRecord(**item) for item in read_json(path)]
=======
    return [PaperRecord(**row) for row in read_json(path)]
>>>>>>> ndmnhat
