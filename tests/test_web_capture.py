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
    / "web_capture.py"
)
SPEC = importlib.util.spec_from_file_location("web_capture", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class WebCaptureTests(unittest.TestCase):
    def test_parser_prefers_article_content(self) -> None:
        parser = MODULE.ReadableHTML()
        parser.feed(
            "<html><head><title>Example</title></head><body>"
            "<nav>Navigation</nav><article><h1>Story</h1><p>"
            + "Real article sentence. " * 20
            + "</p><div><p>Ending.</p></div></article><footer>Footer</footer>"
            "</body></html>"
        )
        text = parser.readable_text()
        self.assertEqual(parser.title(), "Example")
        self.assertIn("Real article sentence.", text)
        self.assertIn("Ending.", text)
        self.assertNotIn("Navigation", text)
        self.assertNotIn("Footer", text)

    def test_staged_visible_text_writes_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "visible.txt"
            source.write_text("Visible article evidence. " * 20, encoding="utf-8")
            args = type(
                "Args",
                (),
                {
                    "url": "https://example.com/article",
                    "output_dir": str(root / "output"),
                    "staged_text": str(source),
                    "title": "Visible article",
                },
            )()
            receipt, code = MODULE.capture(args)
            self.assertEqual(code, 0)
            self.assertEqual(receipt["acquisition_method"], "authorized_browser")
            self.assertEqual(receipt["content_status"], "full_text")
            self.assertTrue((root / "output" / "content.md").is_file())

    def test_private_network_url_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "private network"):
            MODULE.validate_public_url("http://127.0.0.1/private")


if __name__ == "__main__":
    unittest.main()
