from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "cyber-bookhouse"
    / "scripts"
    / "render_diagram.py"
)
SPEC = importlib.util.spec_from_file_location("render_diagram", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RenderDiagramTests(unittest.TestCase):
    def sample(self, kind: str = "flow") -> dict:
        return {
            "title": "内容处理 SOP",
            "subtitle": "有证据才继续",
            "type": kind,
            "nodes": [
                {"id": "a", "title": "收到链接", "description": "识别来源"},
                {"id": "b", "title": "取得正文", "description": "保留证据"},
                {"id": "c", "title": "写入笔记", "description": "打开验收"},
            ],
        }

    def test_all_layouts_render_accessible_svg(self) -> None:
        for kind in MODULE.KINDS:
            spec = MODULE.validate(self.sample(kind))
            svg = MODULE.render_svg(spec)
            self.assertIn('<svg xmlns="http://www.w3.org/2000/svg"', svg)
            self.assertIn('role="img"', svg)
            self.assertIn("内容处理 SOP", svg)
            self.assertNotIn("<script", svg)

    def test_unknown_edges_are_rejected(self) -> None:
        sample = self.sample()
        sample["edges"] = [{"from": "a", "to": "missing"}]
        with self.assertRaisesRegex(ValueError, "edge endpoints"):
            MODULE.validate(sample)

    def test_example_spec_generates_portable_pair(self) -> None:
        example = SCRIPT.parents[1] / "examples" / "structured-sop.json"
        with tempfile.TemporaryDirectory() as folder:
            spec = MODULE.validate(json.loads(example.read_text(encoding="utf-8")))
            output = Path(folder)
            svg = output / "diagram.svg"
            page = output / "diagram.html"
            MODULE.atomic_text(svg, MODULE.render_svg(spec))
            MODULE.atomic_text(page, MODULE.render_html(spec, svg.name))
            self.assertTrue(svg.is_file())
            self.assertIn('src="diagram.svg"', page.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
