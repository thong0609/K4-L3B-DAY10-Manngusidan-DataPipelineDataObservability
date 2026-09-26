from __future__ import annotations

from dataclasses import asdict, dataclass
from html.parser import HTMLParser
import logging
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.config import Settings
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


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord.

    Cac buoc:
    1. Duyet `payload["message"]["items"]`.
    2. Lay DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuan hoa text va bo record khong hop le.
    4. Tra ve list `PaperRecord`.
    """
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

    Cac buoc:
    1. Tao params tu `settings.source_query`, `settings.source_filter`, `settings.max_results`.
    2. Retry loi mang/5xx; fallback ngay khi 429 hoac sau khi retry that bai.
    3. Chi luu raw response hop le vao `settings.paths.raw_api_response`.
    4. Parse payload bang `parse_crossref_payload`.
    5. Luu records vao `settings.paths.raw_records_json`.
    """
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

    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh `PaperRecord`."""
    return [PaperRecord(**item) for item in read_json(path)]
