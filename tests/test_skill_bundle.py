from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "skills" / "cyber-bookhouse"


class SkillBundleTests(unittest.TestCase):
    def test_runtime_resources_are_bundled(self) -> None:
        required = (
            "LICENSE",
            "SKILL.md",
            "release.json",
            "scripts/setup_state.py",
            "scripts/install_skill.py",
            "scripts/update_skill.py",
            "scripts/dependency_doctor.py",
            "scripts/youtube_capture.py",
            "scripts/web_capture.py",
            "scripts/media_capture.py",
            "scripts/render_diagram.py",
            "references/capabilities.md",
            "references/runtime-models.md",
            "references/wechat-channels.md",
            "references/updates.md",
            "references/windows.md",
            "references/claude.md",
            "references/feishu-entry.md",
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
            "references/runtime-models.md",
            "references/wechat-channels.md",
            "references/updates.md",
            "references/claude.md",
            "references/feishu-entry.md",
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

    def test_skill_frontmatter_matches_open_agent_skills_core(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = text.split("---", 2)[1]
        keys = {
            line.split(":", 1)[0].strip()
            for line in frontmatter.splitlines()
            if ":" in line
        }
        self.assertEqual(keys, {"name", "description"})
        self.assertIn("name: cyber-bookhouse", frontmatter)
        self.assertNotIn("sanwei", text.lower())
        description = next(
            line.split(":", 1)[1].strip()
            for line in frontmatter.splitlines()
            if line.startswith("description:")
        )
        self.assertLessEqual(len(description), 1024)

    def test_portable_installer_copies_and_backs_up(self) -> None:
        script = ROOT / "scripts" / "install_skill.py"
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            first = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--target",
                    "both",
                    "--home",
                    str(home),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(first.stdout)
            self.assertEqual(payload["results"]["codex"]["status"], "installed")
            self.assertEqual(payload["results"]["claude"]["status"], "installed")
            self.assertTrue(
                (home / ".agents/skills/cyber-bookhouse/SKILL.md").is_file()
            )
            self.assertTrue(
                (home / ".claude/skills/cyber-bookhouse/SKILL.md").is_file()
            )

            second = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--target",
                    "both",
                    "--home",
                    str(home),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(second.stdout)
            self.assertEqual(payload["results"]["codex"]["status"], "already_current")
            self.assertEqual(payload["results"]["claude"]["status"], "already_current")

            installed = home / ".claude/skills/cyber-bookhouse/SKILL.md"
            installed.write_text("local change", encoding="utf-8")
            third = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--target",
                    "claude",
                    "--home",
                    str(home),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(third.stdout)
            self.assertEqual(payload["results"]["claude"]["status"], "installed")
            backup = Path(payload["results"]["claude"]["backup"])
            self.assertTrue(backup.is_dir())
            self.assertEqual(
                (backup / "SKILL.md").read_text(encoding="utf-8"),
                "local change",
            )

    def test_portable_installer_archives_legacy_id_outside_skill_scan_root(
        self,
    ) -> None:
        script = ROOT / "scripts" / "install_skill.py"
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            legacy = home / ".agents/skills/sanwei"
            legacy.mkdir(parents=True)
            (legacy / "SKILL.md").write_text("legacy install", encoding="utf-8")
            run = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--target",
                    "codex",
                    "--home",
                    str(home),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(run.stdout)
            backups = payload["results"]["codex"]["legacy_backups"]
            self.assertEqual(len(backups), 1)
            self.assertFalse(legacy.exists())
            self.assertTrue(Path(backups[0]).is_dir())
            self.assertFalse(str(Path(backups[0])).startswith(str(legacy.parent)))
            self.assertTrue(
                (home / ".agents/skills/cyber-bookhouse/SKILL.md").is_file()
            )

    def test_release_archive_has_one_portable_skill_root(self) -> None:
        builder = Path(__file__).resolve().parents[1] / "scripts" / "build_release.py"
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / "cyber-bookhouse.zip"
            run = subprocess.run(
                [sys.executable, str(builder), "--output", str(archive)],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(run.stdout)
            self.assertEqual(payload["layout"], "cyber-bookhouse/SKILL.md")
            self.assertEqual(
                payload["targets"], ["Codex", "Claude Code", "WorkBuddy"]
            )
            with zipfile.ZipFile(archive) as bundle:
                names = bundle.namelist()
            self.assertIn("cyber-bookhouse/SKILL.md", names)
            self.assertIn("cyber-bookhouse/scripts/install_skill.py", names)
            self.assertIn("cyber-bookhouse/references/claude.md", names)
            self.assertFalse(any("__pycache__" in name for name in names))


if __name__ == "__main__":
    unittest.main()
