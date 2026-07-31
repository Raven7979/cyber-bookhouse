from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "sanwei"
    / "scripts"
    / "dependency_doctor.py"
)
SPEC = importlib.util.spec_from_file_location("dependency_doctor", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DependencyDoctorTests(unittest.TestCase):
    def test_report_has_every_documented_capability(self) -> None:
        payload = MODULE.report()
        self.assertEqual(
            set(payload["capabilities"]),
            {
                "youtube",
                "media",
                "feishu_docs",
                "feishu_input",
                "local_asr",
                "visible_browser",
                "public_web",
            },
        )

    def test_external_software_has_official_source(self) -> None:
        payload = MODULE.report()
        for name, item in payload["capabilities"].items():
            if name in {"visible_browser", "public_web"}:
                continue
            sources = item.get("official_sources") or [item.get("official_source")]
            self.assertTrue(all(source.startswith("https://") for source in sources))

    def test_windows_report_uses_powershell_and_requires_host_check(self) -> None:
        payload = MODULE.report("Windows", {})
        self.assertEqual(payload["platform"]["support_level"], "beta")
        self.assertEqual(payload["platform"]["shell"], "PowerShell")
        self.assertTrue(payload["platform"]["host_verification_required"])

    def test_windows_asr_excludes_apple_only_mlx(self) -> None:
        payload = MODULE.local_asr("Windows")
        self.assertNotIn("mlx_whisper", payload["commands"])
        self.assertNotIn("mlx_whisper", payload["modules"])
        self.assertEqual(
            payload["official_sources"], ["https://github.com/openai/whisper"]
        )

    def test_windows_obsidian_override_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            application = Path(temporary) / "Obsidian.exe"
            application.write_bytes(b"")
            payload = MODULE.report(
                "Windows", {"CYBER_SANWEI_OBSIDIAN_APP": str(application)}
            )
        self.assertEqual(payload["core"]["status"], "ready")
        self.assertEqual(payload["core"]["obsidian"], str(application))


if __name__ == "__main__":
    unittest.main()
