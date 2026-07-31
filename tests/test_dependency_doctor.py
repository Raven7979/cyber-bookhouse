from __future__ import annotations

import importlib.util
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


if __name__ == "__main__":
    unittest.main()
