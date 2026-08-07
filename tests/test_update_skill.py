from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1] / "skills" / "cyber-bookhouse"
SCRIPT = ROOT / "scripts" / "update_skill.py"
SPEC = importlib.util.spec_from_file_location("cyber_bookhouse_update", SCRIPT)
assert SPEC and SPEC.loader
UPDATER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(UPDATER)


def make_archive(source: Path, destination: Path) -> None:
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                archive.write(path, Path("cyber-bookhouse") / path.relative_to(source))


class UpdateSkillTests(unittest.TestCase):
    def test_latest_release_requires_build_marker_and_digest(self) -> None:
        payload = {
            "tag_name": "v0.2.3",
            "body": "<!-- cyber-bookhouse-build: 1 -->",
            "draft": False,
            "prerelease": False,
            "html_url": "https://github.com/Raven7979/cyber-bookhouse/releases/tag/v0.2.3",
            "assets": [
                {
                    "name": "cyber-bookhouse.zip",
                    "state": "uploaded",
                    "digest": f"sha256:{'a' * 64}",
                    "browser_download_url": "https://github.com/Raven7979/cyber-bookhouse/releases/download/v0.2.3/cyber-bookhouse.zip",
                }
            ],
        }
        with mock.patch.object(UPDATER, "request_json", return_value=payload):
            release = UPDATER.latest_release()
        self.assertEqual(release["version"], "0.2.3")
        self.assertEqual(release["build"], 1)
        self.assertEqual(release["sha256"], "a" * 64)

    def test_same_version_higher_build_is_an_update(self) -> None:
        self.assertTrue(
            UPDATER.update_available(
                {"version": "0.2.2", "build": 1},
                {"version": "0.2.2", "build": 2},
            )
        )
        self.assertFalse(
            UPDATER.update_available(
                {"version": "0.2.2", "build": 2},
                {"version": "0.2.2", "build": 2},
            )
        )

    def test_archive_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root / "unsafe.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("cyber-bookhouse/../escaped", "bad")
            with self.assertRaisesRegex(ValueError, "Unsafe path"):
                UPDATER.validate_and_extract(
                    archive,
                    root / "out",
                    {"version": "0.2.3", "build": 1},
                )

    def test_apply_update_replaces_installed_skill_and_keeps_backup(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            home = temp / "home"
            installed = home / ".agents" / "skills" / "cyber-bookhouse"
            shutil.copytree(ROOT, installed, ignore=shutil.ignore_patterns("__pycache__"))
            (installed / "release.json").write_text(
                json.dumps({"version": "0.2.2", "build": 2}),
                encoding="utf-8",
            )
            archive = temp / "cyber-bookhouse.zip"
            make_archive(ROOT, archive)
            release = {
                "version": "0.2.3",
                "build": 1,
                "tag": "v0.2.3",
                "download_url": "https://github.com/Raven7979/cyber-bookhouse/releases/download/v0.2.3/cyber-bookhouse.zip",
                "sha256": "unused-by-mocked-download",
                "release_url": "https://github.com/Raven7979/cyber-bookhouse/releases/tag/v0.2.3",
            }

            def copy_download(_: dict[str, object], destination: Path) -> None:
                shutil.copy2(archive, destination)

            with (
                mock.patch.object(UPDATER, "skill_root", return_value=installed),
                mock.patch.object(UPDATER, "latest_release", return_value=release),
                mock.patch.object(UPDATER, "download_asset", side_effect=copy_download),
            ):
                result = UPDATER.apply_update("auto", home)

            self.assertEqual(result["status"], "updated")
            identity = json.loads((installed / "release.json").read_text(encoding="utf-8"))
            self.assertEqual(identity, {"version": "0.2.3", "build": 1})
            backup = Path(result["install"]["results"]["codex"]["backup"])
            self.assertTrue(backup.is_dir())
            old_identity = json.loads((backup / "release.json").read_text(encoding="utf-8"))
            self.assertEqual(old_identity, {"version": "0.2.2", "build": 2})


if __name__ == "__main__":
    unittest.main()
