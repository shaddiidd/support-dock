from __future__ import annotations

import io
import re
from collections import Counter
from pathlib import Path
from typing import List

from bs4 import BeautifulSoup
from docx import Document as DocxDocument
from pypdf import PdfReader

from app.services.storage import SUPPORTED_EXTENSIONS

NAV_LINE = re.compile(
    r"^(home|menu|skip to (content|main)|table of contents|copyright|all rights reserved)\b",
    re.I,
)
PAGE_NUMBER = re.compile(
    r"^(?:page\s+)?\d+(?:\s*(?:of|/)\s*\d+)?$|^[-–—•·]+\s*\d+\s*[-–—•·]+$",
    re.I,
)


class ExtractionError(Exception):
    pass


def extract_text(filename: str, content_type: str, data: bytes) -> str:
    ext = Path(filename or "").suffix.lower()
    try:
        if ext == ".pdf" or content_type == "application/pdf":
            return _from_pdf(data)
        if ext == ".docx" or "wordprocessingml" in (content_type or ""):
            return _from_docx(data)
        if ext in {".html", ".htm"} or content_type == "text/html":
            return _from_html(data)
        if ext in SUPPORTED_EXTENSIONS:
            return _from_plain(data)
    except ExtractionError:
        raise
    except Exception as exc:
        raise ExtractionError("Failed to extract text from this file.") from exc
    raise ExtractionError("This file type is not supported.")


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _from_plain(data: bytes) -> str:
    return _normalize(_decode(data))


def _from_html(data: bytes) -> str:
    try:
        soup = BeautifulSoup(_decode(data), "lxml")
    except Exception:
        soup = BeautifulSoup(_decode(data), "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "form", "aside"]):
        tag.decompose()
    for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        level = int(heading.name[1])
        text = heading.get_text(" ", strip=True)
        if text:
            heading.string = f"\n{'#' * level} {text}\n"
    text = soup.get_text("\n")
    return _normalize(text)


def _from_docx(data: bytes) -> str:
    document = DocxDocument(io.BytesIO(data))
    lines: List[str] = []
    for paragraph in document.paragraphs:
        text = (paragraph.text or "").strip()
        if not text:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        style = (paragraph.style.name or "") if paragraph.style else ""
        match = re.match(r"Heading\s+(\d+)", style, re.I)
        if match:
            lines.append(f"{'#' * int(match.group(1))} {text}")
        else:
            lines.append(text)
    return _normalize("\n".join(lines))


def _from_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    pages: List[List[str]] = []
    for page in reader.pages:
        raw = page.extract_text() or ""
        pages.append([line.strip() for line in raw.splitlines() if line.strip()])

    repeated = _repeated_lines(pages)
    cleaned_pages = []
    for lines in pages:
        kept = [
            line
            for line in lines
            if line not in repeated and not PAGE_NUMBER.match(line) and not NAV_LINE.match(line)
        ]
        cleaned_pages.append("\n".join(kept))
    return _normalize("\n\n".join(cleaned_pages))


def _repeated_lines(pages: List[List[str]]) -> set:
    if len(pages) < 2:
        return set()
    counts: Counter = Counter()
    for lines in pages:
        for line in set(lines):
            if len(line) <= 80:
                counts[line] += 1
    threshold = max(2, int(len(pages) * 0.5))
    return {line for line, count in counts.items() if count >= threshold}


def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x0c", "\n")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    lines = []
    for raw in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", raw).strip()
        if PAGE_NUMBER.match(line) or NAV_LINE.match(line):
            continue
        lines.append(line)

    joined: List[str] = []
    for line in lines:
        if not line:
            if joined and joined[-1] != "":
                joined.append("")
            continue
        if (
            joined
            and joined[-1]
            and not joined[-1].startswith("#")
            and not re.search(r"[.!?:]$", joined[-1])
            and line[:1].islower()
        ):
            joined[-1] = f"{joined[-1]} {line}"
            continue
        joined.append(line)

    collapsed = re.sub(r"\n{3,}", "\n\n", "\n".join(joined)).strip()
    if not collapsed:
        raise ExtractionError(
            "No text could be extracted. Scanned or image-only files are not supported."
        )
    return collapsed
