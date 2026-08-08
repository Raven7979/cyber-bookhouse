#!/usr/bin/env python3

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "cyber-bookhouse" / "scripts"))

from visual_gate import detect, finalize, verify  # noqa: E402


class VisualGateTest(unittest.TestCase):
    def test_detects_layered_framework(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.txt"
            source.write_text("内容提出工具层、组织层、商业层的三层进化模型。", encoding="utf-8")
            report = detect([source])
        self.assertTrue(report["required"])
        self.assertEqual(report["diagram_type"], "relationship")
        self.assertIn("layers", report["trigger_categories"])

    def test_plain_content_is_explicitly_not_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.txt"
            source.write_text("这是一段没有结构关系的简单说明。", encoding="utf-8")
            report = detect([source])
        self.assertFalse(report["required"])
        self.assertEqual(verify(report), [])

    def test_force_type_requires_diagram(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.txt"
            source.write_text("普通内容", encoding="utf-8")
            report = detect([source], "architecture")
        self.assertTrue(report["required"])
        self.assertEqual(report["trigger_categories"], ["user_requested"])

    def test_detects_english_architecture(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.txt"
            source.write_text("The system architecture shows a client, gateway, and server data flow.", encoding="utf-8")
            report = detect([source])
        self.assertTrue(report["required"])
        self.assertEqual(report["diagram_type"], "architecture")

    def test_finalize_and_verify_complete_diagram(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_text = root / "source.txt"
            source_text.write_text("系统架构包含客户端、网关和服务端。", encoding="utf-8")
            report_path = root / "visual-report.json"
            report_path.write_text(json.dumps(detect([source_text]), ensure_ascii=False), encoding="utf-8")
            diagram = root / "diagram.mmd"
            diagram.write_text("flowchart LR\n A[客户端] --> B[网关]\n B --> C[服务端]\n", encoding="utf-8")
            preview = root / "diagram.png"
            preview.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 200)
            check = root / "diagram-check.json"
            check.write_text(
                json.dumps(
                    {
                        "code": 0,
                        "data": {
                            "check": {
                                "summary": {"textOverflow": 0, "nodeOverlap": 0, "textOcclusion": 0}
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            review = root / "diagram-review.json"
            review.write_text(
                json.dumps(
                    {
                        "status": "pass",
                        "text_readable": True,
                        "no_overlap": True,
                        "no_cropping": True,
                        "evidence_alignment": True,
                        "relationship_errors": [],
                    }
                ),
                encoding="utf-8",
            )
            report = finalize(report_path, root, diagram, preview, check, review)
            self.assertEqual(verify(report, root), [])

    def test_rejects_failed_visual_review(self) -> None:
        report = {
            "required": True,
            "diagram_type": "architecture",
            "status": "pending",
            "ready": False,
            "artifacts": {},
        }
        errors = verify(report)
        self.assertIn("visual_required_not_complete", errors)
        self.assertIn("visual_preview_missing", errors)


if __name__ == "__main__":
    unittest.main()
