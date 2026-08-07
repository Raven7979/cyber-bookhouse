#!/usr/bin/env python3
"""Validate the immutable reader-facing Markdown contract for cyber-bookhouse."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


STANDARD_HEADINGS = (
    "来源",
    "一句话摘要",
    "核心内容",
    "内容脉络",
    "关键事实与待验证",
    "自动标签",
)
MEDIA_HEADINGS = ("逐字稿与画面证据", "校对记录")
DISTILLED_HEADING = "蒸馏笔记"
MEDIA_TYPES = {"video", "audio", "podcast"}
TRANSCRIPT_READY = {"official", "asr_raw", "asr_proofread"}
PLACEHOLDER_RE = re.compile(r"\{\{.*?\}\}|TODO|TBD|待填写|示例内容", re.IGNORECASE | re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)\s*$", re.MULTILINE)


def _frontmatter(note: str) -> tuple[str, str]:
    match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", note, re.DOTALL)
    if not match:
        return "", note
    return match.group(1), note[match.end() :]


def _scalar(frontmatter: str, key: str) -> str:
    match = re.search(rf"(?m)^{re.escape(key)}:\s*[\"']?([^\n\"']*)[\"']?\s*$", frontmatter)
    return match.group(1).strip() if match else ""


def _headings(body: str) -> list[dict[str, object]]:
    return [
        {
            "level": len(match.group(1)),
            "text": match.group(2).strip(),
            "start": match.start(),
            "end": match.end(),
        }
        for match in HEADING_RE.finditer(body)
    ]


def _section(body: str, headings: list[dict[str, object]], heading: dict[str, object]) -> str:
    index = headings.index(heading)
    end = headings[index + 1]["start"] if index + 1 < len(headings) else len(body)
    return body[int(heading["end"]) : int(end)].strip()


def expected_headings(metadata: dict[str, str]) -> tuple[list[str], list[str]]:
    mode = metadata["note_mode"]
    content_type = metadata["content_type"]
    media_evidence = content_type in MEDIA_TYPES and (
        metadata["media_status"] == "local"
        or metadata["transcript_status"] in TRANSCRIPT_READY
    )
    errors: list[str] = []
    if mode == "standard":
        expected = list(STANDARD_HEADINGS)
        if media_evidence:
            expected.extend(MEDIA_HEADINGS)
    elif mode == "detailed":
        expected = list(STANDARD_HEADINGS)
        if media_evidence:
            expected.extend(MEDIA_HEADINGS)
        expected.append(DISTILLED_HEADING)
    elif mode == "distilled":
        if content_type in MEDIA_TYPES:
            if not media_evidence:
                errors.append("distilled_media_evidence_missing")
            expected = ["来源", *MEDIA_HEADINGS, DISTILLED_HEADING]
        else:
            if metadata["content_status"] != "full_text":
                errors.append("distilled_full_text_missing")
            expected = ["来源", DISTILLED_HEADING]
    else:
        errors.append("invalid_note_mode")
        expected = []
    return expected, errors


def validate(note: str) -> dict[str, object]:
    frontmatter, body = _frontmatter(note)
    metadata = {
        key: _scalar(frontmatter, key)
        for key in (
            "title",
            "source_url",
            "content_type",
            "note_mode",
            "content_status",
            "media_status",
            "transcript_status",
        )
    }
    missing_metadata = [key for key, value in metadata.items() if not value]
    expected, evidence_errors = expected_headings(metadata)
    headings = _headings(body)
    title_headings = [heading for heading in headings if heading["level"] == 1]
    level_two = [heading for heading in headings if heading["level"] == 2]
    found = [str(heading["text"]) for heading in level_two]
    missing = [heading for heading in expected if heading not in found]
    duplicate = [heading for heading in expected if found.count(heading) > 1]
    unexpected = [heading for heading in found if heading not in expected]
    order_ok = found == expected

    empty_sections: list[str] = []
    placeholder_sections: list[str] = []
    for heading in level_two:
        text = str(heading["text"])
        if text not in expected or found.count(text) != 1:
            continue
        section = _section(body, headings, heading)
        if not section:
            empty_sections.append(text)
        elif PLACEHOLDER_RE.search(section):
            placeholder_sections.append(text)

    source_url_ok = False
    source_matches = [heading for heading in level_two if heading["text"] == "来源"]
    if len(source_matches) == 1 and metadata["source_url"]:
        source_url_ok = metadata["source_url"] in _section(body, headings, source_matches[0])

    transcript_timecode_ok = True
    if "逐字稿与画面证据" in expected:
        matches = [heading for heading in level_two if heading["text"] == "逐字稿与画面证据"]
        transcript_timecode_ok = len(matches) == 1 and bool(
            re.search(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", _section(body, headings, matches[0]))
        )

    title_ok = len(title_headings) == 1 and int(title_headings[0]["start"]) < (
        int(level_two[0]["start"]) if level_two else len(body)
    )
    ready = all(
        (
            bool(frontmatter),
            not missing_metadata,
            not evidence_errors,
            title_ok,
            not missing,
            not duplicate,
            not unexpected,
            order_ok,
            not empty_sections,
            not placeholder_sections,
            source_url_ok,
            transcript_timecode_ok,
        )
    )
    return {
        "ready": ready,
        "metadata": metadata,
        "missing_metadata": missing_metadata,
        "evidence_errors": evidence_errors,
        "title_ok": title_ok,
        "expected_headings": expected,
        "found_headings": found,
        "missing_headings": missing,
        "duplicate_headings": duplicate,
        "unexpected_headings": unexpected,
        "heading_order_ok": order_ok,
        "empty_sections": empty_sections,
        "placeholder_sections": placeholder_sections,
        "source_url_ok": source_url_ok,
        "transcript_timecode_ok": transcript_timecode_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("note", type=Path)
    args = parser.parse_args()
    report = validate(args.note.read_text(encoding="utf-8"))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    sys.exit(main())
