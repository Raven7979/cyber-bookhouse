#!/usr/bin/env python3
"""Validate the immutable reader-facing Markdown contract for cyber-bookhouse."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from visual_gate import verify as verify_visual_report


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
MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
OBSIDIAN_IMAGE_RE = re.compile(r"!\[\[([^|\]]+)(?:\|[^\]]*)?\]\]")
REMOTE_IMAGE_RE = re.compile(r"^(?:https?:|data:)", re.IGNORECASE)


def _frontmatter(note: str) -> tuple[str, str]:
    match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", note, re.DOTALL)
    if not match:
        return "", note
    return match.group(1), note[match.end() :]


def _scalar(frontmatter: str, key: str) -> str:
    match = re.search(rf"(?m)^{re.escape(key)}:\s*[\"']?([^\n\"']*)[\"']?\s*$", frontmatter)
    return match.group(1).strip() if match else ""


def _list(frontmatter: str, key: str) -> list[str]:
    match = re.search(
        rf"(?ms)^{re.escape(key)}:\s*(.*?)\n(?=[A-Za-z_][A-Za-z0-9_]*:\s*|\Z)",
        frontmatter + "\n",
    )
    if not match:
        return []
    value = match.group(1).strip()
    if value in {"", "[]"}:
        return []
    return [
        item.strip().strip('"').strip("'")
        for item in re.findall(r"(?m)^\s*-\s+(.+?)\s*$", match.group(1))
    ]


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


def _local_image_references(section: str) -> list[tuple[int, str]]:
    references: list[tuple[int, str]] = []
    for pattern in (MARKDOWN_IMAGE_RE, OBSIDIAN_IMAGE_RE):
        for match in pattern.finditer(section):
            raw_target = match.group(1).strip()
            if pattern is MARKDOWN_IMAGE_RE and raw_target.startswith("<") and ">" in raw_target:
                target = raw_target[1 : raw_target.index(">")]
            else:
                target = raw_target.split(" ", 1)[0]
            if target and not REMOTE_IMAGE_RE.match(target):
                references.append((match.start(), target))
    return sorted(references)


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


def validate(
    note: str,
    *,
    note_path: Path | None = None,
    visual_report: object | None = None,
    visual_root: Path | None = None,
) -> dict[str, object]:
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
            "visual_status",
        )
    }
    visual_assets = _list(frontmatter, "visual_assets")
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
    transcript_section = ""
    if "逐字稿与画面证据" in expected:
        matches = [heading for heading in level_two if heading["text"] == "逐字稿与画面证据"]
        if len(matches) == 1:
            transcript_section = _section(body, headings, matches[0])
        transcript_timecode_ok = bool(
            re.search(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", transcript_section)
        )

    complete_video_declared = (
        metadata["content_type"] == "video" and metadata["content_status"] == "full_text"
    )
    video_media_ok = metadata["media_status"] == "local"
    video_transcript_ok = metadata["transcript_status"] in TRANSCRIPT_READY
    video_images = _local_image_references(transcript_section)
    first_timecode = re.search(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", transcript_section)
    cover_images = {
        target
        for position, target in video_images
        if first_timecode is not None and position < first_timecode.start()
    }
    evidence_images = {
        target
        for position, target in video_images
        if first_timecode is not None and position > first_timecode.start()
    }
    video_images_ok = len(cover_images) >= 1 and len(evidence_images) >= 3
    complete_video_ready = all(
        (
            video_media_ok,
            video_transcript_ok,
            transcript_timecode_ok,
            video_images_ok,
        )
    )

    visual_errors = (
        ["visual_report_missing"]
        if visual_report is None
        else verify_visual_report(visual_report, visual_root)
    )
    visual_required = isinstance(visual_report, dict) and visual_report.get("required") is True
    visual_status_ok = metadata["visual_status"] == (
        "required" if visual_required else "not_required"
    )
    visual_assets_ok = bool(visual_assets) if visual_required else not visual_assets
    visual_reference_ok = True
    visual_asset_files_ok = True
    visual_preview_matches = True
    if visual_required:
        allowed_visual_sections = [
            heading
            for heading in level_two
            if heading["text"] in {"核心内容", "蒸馏笔记"}
        ]
        visual_reference_ok = any(
            re.search(rf"!\[[^\]]*\]\({re.escape(asset)}\)", _section(body, headings, heading))
            for heading in allowed_visual_sections
            for asset in visual_assets
        )
        if note_path is not None:
            visual_asset_files_ok = all((note_path.parent / asset).resolve().is_file() for asset in visual_assets)
        if visual_root is not None and isinstance(visual_report, dict):
            artifacts = visual_report.get("artifacts", {})
            preview = artifacts.get("preview") if isinstance(artifacts, dict) else ""
            if note_path is None or not isinstance(preview, str) or not preview:
                visual_preview_matches = False
            else:
                expected_preview = (visual_root / preview).resolve()
                visual_preview_matches = any(
                    (note_path.parent / asset).resolve() == expected_preview for asset in visual_assets
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
            not complete_video_declared or complete_video_ready,
            not visual_errors,
            visual_status_ok,
            visual_assets_ok,
            visual_reference_ok,
            visual_asset_files_ok,
            visual_preview_matches,
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
        "complete_video_declared": complete_video_declared,
        "complete_video_ready": complete_video_ready,
        "video_media_ok": video_media_ok,
        "video_transcript_ok": video_transcript_ok,
        "video_cover_images": sorted(cover_images),
        "video_evidence_images": sorted(evidence_images),
        "video_images_ok": video_images_ok,
        "visual_required": visual_required,
        "visual_errors": visual_errors,
        "visual_status_ok": visual_status_ok,
        "visual_assets": visual_assets,
        "visual_assets_ok": visual_assets_ok,
        "visual_reference_ok": visual_reference_ok,
        "visual_asset_files_ok": visual_asset_files_ok,
        "visual_preview_matches": visual_preview_matches,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("note", type=Path)
    parser.add_argument("--visual-report", required=True, type=Path)
    args = parser.parse_args()
    visual_report = json.loads(args.visual_report.read_text(encoding="utf-8"))
    report = validate(
        args.note.read_text(encoding="utf-8"),
        note_path=args.note,
        visual_report=visual_report,
        visual_root=args.visual_report.parent,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    sys.exit(main())
