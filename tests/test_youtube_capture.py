from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "cyber-bookhouse"
    / "scripts"
    / "youtube_capture.py"
)
SPEC = importlib.util.spec_from_file_location("youtube_capture", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class YoutubeCaptureTests(unittest.TestCase):
    def test_video_id_from_common_urls(self) -> None:
        self.assertEqual(
            MODULE.video_id("https://youtu.be/YQMPLJl7zTI?t=115"),
            "YQMPLJl7zTI",
        )
        self.assertEqual(
            MODULE.video_id("https://www.youtube.com/watch?v=YQMPLJl7zTI"),
            "YQMPLJl7zTI",
        )
        self.assertEqual(
            MODULE.video_id("https://www.youtube.com/shorts/YQMPLJl7zTI"),
            "YQMPLJl7zTI",
        )

    def test_bot_check_is_a_distinct_failure(self) -> None:
        self.assertEqual(
            MODULE.classify_error("Sign in to confirm you’re not a bot"),
            "youtube_bot_check",
        )
        public = MODULE.public_error(
            "youtube_bot_check", "Try --cookies-from-browser and export credentials"
        )
        self.assertNotIn("cookies-from-browser", public)
        self.assertIn("was not attempted", public)

    def test_vtt_is_converted_to_timestamped_text(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "sample.vtt"
            source.write_text(
                "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nHello world\n\n"
                "00:00:04.000 --> 00:00:05.000\nSecond line\n",
                encoding="utf-8",
            )
            self.assertEqual(
                MODULE.vtt_to_text(source),
                "[00:01] Hello world\n[00:04] Second line",
            )

    def test_staged_visible_transcript_requires_real_text(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "visible.txt"
            source.write_text(
                "[00:01] This is visibly rendered transcript evidence from the page.",
                encoding="utf-8",
            )
            result = MODULE.staged_transcript(source, root / "output")
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["acquisition_method"], "authorized_browser")
            self.assertTrue(Path(result["transcript_path"]).is_file())

    def test_missing_external_tool_returns_install_source(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            args = type(
                "Args",
                (),
                {
                    "url": "https://youtu.be/YQMPLJl7zTI",
                    "output_dir": folder,
                    "staged_transcript": None,
                },
            )()
            with (
                mock.patch.object(MODULE, "oembed_metadata", return_value={}),
                mock.patch.object(MODULE.shutil, "which", return_value=None),
            ):
                receipt, code = MODULE.capture(args)
            self.assertEqual(code, 2)
            self.assertEqual(receipt["status"], "dependency_missing")
            self.assertIn("github.com/yt-dlp", receipt["official_source"])


if __name__ == "__main__":
    unittest.main()
