from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "cyber-bookhouse"
    / "scripts"
    / "media_capture.py"
)
SPEC = importlib.util.spec_from_file_location("media_capture", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class MediaCaptureTests(unittest.TestCase):
    def test_duration_and_video_detection(self) -> None:
        metadata = {
            "format": {"duration": "12.5"},
            "streams": [{"codec_type": "video"}, {"codec_type": "audio"}],
        }
        self.assertEqual(MODULE.duration(metadata), 12.5)
        self.assertTrue(MODULE.has_video(metadata))

    def test_mlx_transcription_command_is_local_and_timestamped(self) -> None:
        command, expected = MODULE.transcription_command(
            "mlx_whisper",
            "/opt/homebrew/bin/mlx_whisper",
            Path("/tmp/sample.mp4"),
            Path("/tmp/output"),
            "zh",
        )
        self.assertIn("mlx-community/whisper-large-v3-turbo", command)
        self.assertIn("vtt", command)
        self.assertIn("zh", command)
        self.assertEqual(expected, "transcript.vtt")

    def test_windows_uses_openai_whisper_even_if_mlx_is_on_path(self) -> None:
        with mock.patch.object(MODULE.shutil, "which", return_value="available"):
            self.assertEqual(MODULE.transcription_backend("Windows"), "whisper")

    def test_missing_ffprobe_returns_official_install_source(self) -> None:
        with mock.patch.object(MODULE.shutil, "which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "ffmpeg.org/download"):
                MODULE.probe(Path("/tmp/sample.mp4"))

    def test_frame_extraction_writes_complete_compatible_jpeg(self) -> None:
        commands = []

        def fake_run(
            command: list[str], timeout: int = 1800
        ) -> subprocess.CompletedProcess:
            commands.append(command)
            Path(command[-1]).write_bytes(b"\xff\xd8frame\xff\xd9")
            return subprocess.CompletedProcess(command, 0, "", "")

        with tempfile.TemporaryDirectory() as temporary:
            with (
                mock.patch.object(MODULE.shutil, "which", return_value="ffmpeg"),
                mock.patch.object(MODULE, "run", side_effect=fake_run),
            ):
                frames = MODULE.extract_frames(
                    Path("/tmp/sample.mp4"), Path(temporary), 1, 3.0
                )
        self.assertEqual(len(frames), 1)
        self.assertIn("-pix_fmt", commands[0])
        self.assertIn("yuvj420p", commands[0])

    def test_frame_extraction_rejects_truncated_jpeg(self) -> None:
        def fake_run(
            command: list[str], timeout: int = 1800
        ) -> subprocess.CompletedProcess:
            Path(command[-1]).write_bytes(b"\xff\xd8truncated")
            return subprocess.CompletedProcess(command, 0, "", "")

        with tempfile.TemporaryDirectory() as temporary:
            with (
                mock.patch.object(MODULE.shutil, "which", return_value="ffmpeg"),
                mock.patch.object(MODULE, "run", side_effect=fake_run),
            ):
                with self.assertRaisesRegex(RuntimeError, "representative frame"):
                    MODULE.extract_frames(
                        Path("/tmp/sample.mp4"), Path(temporary), 1, 3.0
                    )


if __name__ == "__main__":
    unittest.main()
