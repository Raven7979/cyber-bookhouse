#!/usr/bin/env python3

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "cyber-bookhouse" / "scripts"))

from validate_note import validate  # noqa: E402


URL = "https://example.com/source"
NO_VISUAL = {
    "schema_version": 1,
    "required": False,
    "diagram_type": "none",
    "status": "not_required",
    "ready": True,
    "artifacts": {},
}


def checked(value: str, visual_report: object = NO_VISUAL):
    return validate(value, visual_report=visual_report)


def note(mode: str = "standard", content_type: str = "article", media: bool = False) -> str:
    metadata = f"""---
title: Test note
source_url: {URL}
content_type: {content_type}
note_mode: {mode}
content_status: full_text
media_status: {'local' if media else 'not_requested'}
transcript_status: {'asr_proofread' if media else 'unavailable'}
visual_status: not_required
visual_assets: []
---

# Test note
"""
    if mode == "distilled":
        headings = ["来源"]
        if content_type in {"video", "audio", "podcast"}:
            headings += ["逐字稿与画面证据", "校对记录"]
        headings += ["蒸馏笔记"]
    else:
        headings = ["来源", "一句话摘要", "核心内容", "内容脉络", "关键事实与待验证", "自动标签"]
        if media:
            headings += ["逐字稿与画面证据", "校对记录"]
        if mode == "detailed":
            headings += ["蒸馏笔记"]
    parts = [metadata]
    for heading in headings:
        if heading == "来源":
            body = f"原链接：{URL}"
        elif heading == "逐字稿与画面证据":
            body = "**00:00–00:30** 完整语义段。"
        else:
            body = heading + "的有效正文。"
        parts.append(f"## {heading}\n\n{body}")
    return "\n\n".join(parts)


class ValidateNoteTest(unittest.TestCase):
    def test_accepts_standard_article(self) -> None:
        self.assertTrue(checked(note())["ready"])

    def test_accepts_standard_video_with_evidence(self) -> None:
        self.assertTrue(checked(note(content_type="video", media=True))["ready"])

    def test_accepts_distilled_article_and_detailed_video(self) -> None:
        self.assertTrue(checked(note(mode="distilled"))["ready"])
        self.assertTrue(checked(note(mode="detailed", content_type="video", media=True))["ready"])

    def test_rejects_extra_peer_heading(self) -> None:
        value = note().replace("## 内容脉络", "## 原文文案\n\n额外栏目。\n\n## 内容脉络")
        report = checked(value)
        self.assertEqual(report["unexpected_headings"], ["原文文案"])
        self.assertFalse(report["ready"])

    def test_rejects_old_loose_schema(self) -> None:
        value = note().replace("## 内容脉络\n\n内容脉络的有效正文。\n\n", "").replace(
            "## 自动标签\n\n自动标签的有效正文。", "## 可复用结论\n\n旧版正文。"
        )
        report = checked(value)
        self.assertIn("内容脉络", report["missing_headings"])
        self.assertIn("自动标签", report["missing_headings"])
        self.assertIn("可复用结论", report["unexpected_headings"])
        self.assertFalse(report["ready"])

    def test_rejects_source_url_outside_source_section(self) -> None:
        value = note().replace(f"原链接：{URL}", "原链接：未取得", 1)
        report = checked(value)
        self.assertFalse(report["source_url_ok"])
        self.assertFalse(report["ready"])

    def test_rejects_placeholder_and_missing_timecode(self) -> None:
        value = note(content_type="video", media=True).replace("核心内容的有效正文。", "{{待填写}}")
        value = value.replace("**00:00–00:30** 完整语义段。", "没有时间码。")
        report = checked(value)
        self.assertIn("核心内容", report["placeholder_sections"])
        self.assertFalse(report["transcript_timecode_ok"])
        self.assertFalse(report["ready"])

    def test_rejects_distilled_video_without_media_evidence(self) -> None:
        report = checked(note(mode="distilled", content_type="video", media=False))
        self.assertIn("distilled_media_evidence_missing", report["evidence_errors"])
        self.assertFalse(report["ready"])

    def test_rejects_missing_visual_report(self) -> None:
        report = validate(note())
        self.assertEqual(report["visual_errors"], ["visual_report_missing"])
        self.assertFalse(report["ready"])

    def test_requires_embedded_asset_when_visual_is_required(self) -> None:
        required = {
            "schema_version": 1,
            "required": True,
            "diagram_type": "relationship",
            "status": "pending",
            "ready": False,
            "artifacts": {},
        }
        value = note().replace("visual_status: not_required", "visual_status: required")
        report = checked(value, required)
        self.assertFalse(report["visual_assets_ok"])
        self.assertFalse(report["ready"])

    def test_accepts_required_visual_only_after_artifact_and_embed_checks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            note_dir = root / "notes"
            asset_dir = root / "assets"
            note_dir.mkdir()
            asset_dir.mkdir()
            (asset_dir / "diagram.mmd").write_text(
                "flowchart LR\n A[工具层] --> B[组织层]\n B --> C[商业层]\n",
                encoding="utf-8",
            )
            (asset_dir / "diagram.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 200)
            (asset_dir / "diagram-check.json").write_text(
                '{"code":0,"data":{"check":{"summary":{"textOverflow":0,"nodeOverlap":0,"textOcclusion":0}}}}',
                encoding="utf-8",
            )
            (asset_dir / "diagram-review.json").write_text(
                '{"status":"pass","text_readable":true,"no_overlap":true,"no_cropping":true,"evidence_alignment":true,"relationship_errors":[]}',
                encoding="utf-8",
            )
            visual_report = {
                "schema_version": 1,
                "required": True,
                "diagram_type": "relationship",
                "status": "complete",
                "ready": True,
                "artifacts": {
                    "source": "diagram.mmd",
                    "preview": "diagram.png",
                    "check": "diagram-check.json",
                    "review": "diagram-review.json",
                },
            }
            value = note().replace(
                "visual_status: not_required\nvisual_assets: []",
                "visual_status: required\nvisual_assets:\n  - ../assets/diagram.png",
            ).replace(
                "核心内容的有效正文。",
                "核心内容的有效正文。\n\n![三层关系图](../assets/diagram.png)",
            )
            note_path = note_dir / "note.md"
            note_path.write_text(value, encoding="utf-8")
            report = validate(
                value,
                note_path=note_path,
                visual_report=visual_report,
                visual_root=asset_dir,
            )
            self.assertTrue(report["ready"], report)


if __name__ == "__main__":
    unittest.main()
