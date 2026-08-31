from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from app.services.language import detect_language

KEEP_SECTION_WORDS = 500
CHUNK_TARGET_WORDS = 400
CHUNK_MIN_WORDS = 300
CHUNK_MAX_WORDS = 500
OVERLAP_WORDS = 65

HEADING_ATX = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
HEADING_SETEXT_UNDERLINE = re.compile(r"^(=+|-+)\s*$")
HEADING_NUMBERED = re.compile(r"^((?:\d+\.){1,4})\s+(.+)$")
HEADING_ALLCAPS = re.compile(r"^[A-Z][A-Z0-9 ,/&()'._-]{7,}$")
FAQ_QUESTION = re.compile(
    r"^(?:(?:q(?:uestion)?|faq)\s*[:.)-]?\s*)?(how |what |why |when |where |who |can |do |does |is |are ).+\??$",
    re.I,
)
FAQ_LABEL = re.compile(r"^(?:q(?:uestion)?|faq(?:\s*\d+)?)\s*[:.)-]\s*(.+)$", re.I)
ANSWER_LABEL = re.compile(r"^(?:a(?:nswer)?)\s*[:.)-]\s*(.*)$", re.I)
STEP_LINE = re.compile(r"^(?:step\s+\d+[:.)]\s*|\d+[\.)]\s+|[-*•]\s+\d+[\.)]\s+)", re.I)


@dataclass
class Chunk:
    text: str
    heading_path: str
    order: int
    language: str = "en"


def word_count(text: str) -> int:
    return len([part for part in text.split() if part])


def chunk_document(title: str, text: str) -> List[Chunk]:
    sections = _split_sections(text)
    chunks: List[Chunk] = []
    for heading_path, kind, body in sections:
        chunks.extend(_chunk_section(title, heading_path, kind, body))
    numbered = []
    for index, chunk in enumerate(chunks):
        numbered.append(
            Chunk(
                text=_prefix(title, chunk.heading_path, chunk.text),
                heading_path=chunk.heading_path,
                order=index,
                language=detect_language(chunk.text),
            )
        )
    return numbered


def _prefix(title: str, heading_path: str, body: str) -> str:
    lines = [f"Document: {title}"]
    if heading_path:
        lines.append(f"Section: {heading_path}")
    return "\n".join(lines) + "\n\n" + body.strip()


def _split_sections(text: str) -> List[Tuple[str, str, str]]:
    lines = text.split("\n")
    stack: List[Tuple[int, str]] = []
    sections: List[Tuple[str, str, List[str]]] = []
    current_path = ""
    current_kind = "section"
    current_lines: List[str] = []

    def flush() -> None:
        body = "\n".join(current_lines).strip()
        if body:
            sections.append((current_path, current_kind, body.split("\n")))

    index = 0
    while index < len(lines):
        line = lines[index]
        heading = _heading_at(lines, index)
        if heading:
            flush()
            level, heading_text = heading
            stack[:] = [(lvl, title) for lvl, title in stack if lvl < level]
            stack.append((level, heading_text))
            current_path = " > ".join(title for _, title in stack)
            current_kind = "faq" if _is_question(heading_text) else "section"
            current_lines = []
            if HEADING_SETEXT_UNDERLINE.match(lines[index + 1] if index + 1 < len(lines) else ""):
                index += 2
            else:
                index += 1
            continue

        faq = FAQ_LABEL.match(line)
        if faq:
            flush()
            stack[:] = [(lvl, title) for lvl, title in stack if lvl < 6]
            question = faq.group(1).strip()
            current_path = " > ".join([*(title for _, title in stack), question])
            current_kind = "faq"
            current_lines = [line]
            index += 1
            continue

        current_lines.append(line)
        index += 1

    flush()

    result: List[Tuple[str, str, str]] = []
    for path, kind, body_lines in sections:
        body = "\n".join(body_lines).strip()
        if not body:
            continue
        if kind != "faq" and _looks_like_steps(body):
            kind = "steps"
        result.append((path, kind, body))
    return result or [("", "section", text.strip())]


def _heading_at(lines: Sequence[str], index: int) -> Optional[Tuple[int, str]]:
    line = lines[index].strip()
    if not line:
        return None
    atx = HEADING_ATX.match(line)
    if atx:
        return len(atx.group(1)), atx.group(2).strip()
    if index + 1 < len(lines) and HEADING_SETEXT_UNDERLINE.match(lines[index + 1].strip()):
        level = 1 if lines[index + 1].strip().startswith("=") else 2
        return level, line
    numbered = HEADING_NUMBERED.match(line)
    if numbered and word_count(line) <= 12 and not STEP_LINE.match(line):
        return min(line.count(".") + 1, 6), numbered.group(2).strip()
    if HEADING_ALLCAPS.match(line) and not re.search(r"[.!?]$", line) and word_count(line) <= 10:
        return 2, line.title()
    if _is_question(line) and word_count(line) <= 20:
        return 3, line.rstrip("?") + "?"
    return None


def _is_question(text: str) -> bool:
    stripped = text.strip()
    return bool(FAQ_QUESTION.match(stripped) or stripped.endswith("?"))


def _looks_like_steps(body: str) -> bool:
    lines = [line for line in body.split("\n") if line.strip()]
    if len(lines) < 2:
        return False
    stepped = sum(1 for line in lines if STEP_LINE.match(line))
    return stepped >= 2 and stepped / len(lines) >= 0.4


def _chunk_section(title: str, heading_path: str, kind: str, body: str) -> List[Chunk]:
    words = body.split()
    if len(words) <= KEEP_SECTION_WORDS:
        return [Chunk(text=body.strip(), heading_path=heading_path, order=0)]

    if kind == "faq":
        produced = _chunk_faq(heading_path, body)
    elif kind == "steps":
        produced = _chunk_steps(heading_path, body)
    else:
        produced = _chunk_words(heading_path, words)

    flattened: List[Chunk] = []
    for chunk in produced:
        if word_count(chunk.text) <= CHUNK_MAX_WORDS:
            flattened.append(chunk)
            continue
        flattened.extend(_chunk_words(chunk.heading_path, chunk.text.split()))
    return flattened or [Chunk(text=body.strip(), heading_path=heading_path, order=0)]


def _chunk_faq(heading_path: str, body: str) -> List[Chunk]:
    question, answer = _split_question_answer(heading_path, body)
    answer_words = answer.split()
    if word_count(body) <= KEEP_SECTION_WORDS:
        return [Chunk(text=body.strip(), heading_path=heading_path, order=0)]

    pieces = _window(answer_words, CHUNK_TARGET_WORDS, OVERLAP_WORDS)
    chunks = []
    for piece in pieces:
        text = f"{question}\n\n{piece}".strip() if question not in piece else piece
        chunks.append(Chunk(text=text, heading_path=heading_path, order=0))
    return chunks


def _split_question_answer(heading_path: str, body: str) -> Tuple[str, str]:
    lines = body.split("\n")
    first = lines[0].strip()
    labeled = FAQ_LABEL.match(first)
    if labeled:
        return labeled.group(1).strip(), "\n".join(lines[1:]).strip()
    if first.endswith("?") or _is_question(first):
        return first, "\n".join(lines[1:]).strip()
    answer = ANSWER_LABEL.match(first)
    if answer:
        rest = "\n".join([answer.group(1), *lines[1:]]).strip()
        question = heading_path.split(" > ")[-1] if heading_path else ""
        return question, rest
    question = heading_path.split(" > ")[-1] if heading_path else ""
    return question, body


def _chunk_steps(heading_path: str, body: str) -> List[Chunk]:
    steps = _group_steps(body)
    chunks: List[str] = []
    current: List[str] = []
    for step in steps:
        candidate = current + [step]
        if word_count("\n".join(candidate)) <= CHUNK_MAX_WORDS or not current:
            current = candidate
            continue
        chunks.append("\n".join(current).strip())
        overlap = current[-1] if current else ""
        current = [overlap, step] if overlap else [step]
    if current:
        chunks.append("\n".join(current).strip())
    return [Chunk(text=item, heading_path=heading_path, order=0) for item in chunks]


def _group_steps(body: str) -> List[str]:
    groups: List[str] = []
    current: List[str] = []
    for line in body.split("\n"):
        if STEP_LINE.match(line) and current:
            groups.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        groups.append("\n".join(current).strip())
    return groups or [body]


def _chunk_words(heading_path: str, words: List[str]) -> List[Chunk]:
    pieces = _window(words, CHUNK_TARGET_WORDS, OVERLAP_WORDS)
    return [Chunk(text=piece, heading_path=heading_path, order=0) for piece in pieces]


def _window(words: List[str], size: int, overlap: int) -> List[str]:
    if not words:
        return []
    size = min(max(size, CHUNK_MIN_WORDS), CHUNK_MAX_WORDS)
    overlap = min(max(overlap, 50), 80)
    chunks: List[str] = []
    start = 0
    while start < len(words):
        end = min(start + size, len(words))
        remaining = len(words) - end
        if 0 < remaining < 80:
            end = len(words)
        chunks.append(" ".join(words[start:end]).strip())
        if end >= len(words):
            break
        start = max(end - overlap, start + 1)
    return [item for item in chunks if item]
