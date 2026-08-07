#!/usr/bin/env python3

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "cyber-bookhouse" / "scripts"))

from validate_note import validate  # noqa: E402


URL = "https://example.com/source"


def note(mode: str = "standard", content_type: str = "article", media: bool = False) -> str:
    metadata = f"""---
title: Test note
source_url: {URL}
content_type: {content_type}
note_mode: {mode}
content_status: full_text
media_status: {'local' if media else 'not_requested'}
transcript_status: {'asr_proofread' if media else 'unavailable'}
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
        self.assertTrue(validate(note())["ready"])

    def test_accepts_standard_video_with_evidence(self) -> None:
        self.assertTrue(validate(note(content_type="video", media=True))["ready"])

    def test_accepts_distilled_article_and_detailed_video(self) -> None:
        self.assertTrue(validate(note(mode="distilled"))["ready"])
        self.assertTrue(validate(note(mode="detailed", content_type="video", media=True))["ready"])

    def test_rejects_extra_peer_heading(self) -> None:
        value = note().replace("## 内容脉络", "## 原文文案\n\n额外栏目。\n\n## 内容脉络")
        report = validate(value)
        self.assertEqual(report["unexpected_headings"], ["原文文案"])
        self.assertFalse(report["ready"])

    def test_rejects_old_loose_schema(self) -> None:
        value = note().replace("## 内容脉络\n\n内容脉络的有效正文。\n\n", "").replace(
            "## 自动标签\n\n自动标签的有效正文。", "## 可复用结论\n\n旧版正文。"
        )
        report = validate(value)
        self.assertIn("内容脉络", report["missing_headings"])
        self.assertIn("自动标签", report["missing_headings"])
        self.assertIn("可复用结论", report["unexpected_headings"])
        self.assertFalse(report["ready"])

    def test_rejects_source_url_outside_source_section(self) -> None:
        value = note().replace(f"原链接：{URL}", "原链接：未取得", 1)
        report = validate(value)
        self.assertFalse(report["source_url_ok"])
        self.assertFalse(report["ready"])

    def test_rejects_placeholder_and_missing_timecode(self) -> None:
        value = note(content_type="video", media=True).replace("核心内容的有效正文。", "{{待填写}}")
        value = value.replace("**00:00–00:30** 完整语义段。", "没有时间码。")
        report = validate(value)
        self.assertIn("核心内容", report["placeholder_sections"])
        self.assertFalse(report["transcript_timecode_ok"])
        self.assertFalse(report["ready"])

    def test_rejects_distilled_video_without_media_evidence(self) -> None:
        report = validate(note(mode="distilled", content_type="video", media=False))
        self.assertIn("distilled_media_evidence_missing", report["evidence_errors"])
        self.assertFalse(report["ready"])


if __name__ == "__main__":
    unittest.main()
