from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "skills" / "sanwei"


class SkillBundleTests(unittest.TestCase):
    def test_runtime_resources_are_bundled(self) -> None:
        required = (
            "SKILL.md",
            "scripts/setup_state.py",
            "scripts/dependency_doctor.py",
            "scripts/youtube_capture.py",
            "scripts/web_capture.py",
            "scripts/media_capture.py",
            "scripts/render_diagram.py",
            "references/capabilities.md",
            "references/windows.md",
            "references/wechat-assistant.md",
            "references/youtube.md",
            "references/web.md",
            "references/media.md",
            "references/visualizations.md",
            "references/distillation.md",
            "references/note-schema.md",
            "examples/structured-sop.json",
        )
        missing = [name for name in required if not (ROOT / name).is_file()]
        self.assertEqual(missing, [])

    def test_skill_references_resolve(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for target in (
            "references/capabilities.md",
            "references/youtube.md",
            "references/distillation.md",
            "references/visualizations.md",
            "scripts/dependency_doctor.py",
            "scripts/youtube_capture.py",
            "scripts/web_capture.py",
            "scripts/media_capture.py",
            "scripts/render_diagram.py",
        ):
            self.assertIn(target, text)
            self.assertTrue((ROOT / target).is_file())


if __name__ == "__main__":
    unittest.main()
