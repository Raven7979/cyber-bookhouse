#!/usr/bin/env python3
"""Inspect local media, extract representative frames, and transcribe locally."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def run(command: list[str], timeout: int = 1800) -> subprocess.CompletedProcess:
    return subprocess.run(
        command, check=False, capture_output=True, text=True, timeout=timeout
    )


def probe(path: Path) -> dict:
    executable = shutil.which("ffprobe")
    if not executable:
        raise RuntimeError("ffprobe is missing. Install FFmpeg from https://ffmpeg.org/download.html")
    result = run(
        [
            executable,
            "-v",
            "error",
            "-show_entries",
            "format=duration,format_name:stream=index,codec_type,codec_name,width,height",
            "-of",
            "json",
            str(path),
        ],
        timeout=120,
    )
    if result.returncode:
        raise RuntimeError((result.stderr or "ffprobe could not read this file.").strip())
    return json.loads(result.stdout)


def duration(metadata: dict) -> float:
    try:
        return max(0.0, float(metadata.get("format", {}).get("duration") or 0))
    except (TypeError, ValueError):
        return 0.0


def has_video(metadata: dict) -> bool:
    return any(item.get("codec_type") == "video" for item in metadata.get("streams", []))


def extract_frames(path: Path, output: Path, count: int, seconds: float) -> list[str]:
    if count <= 0:
        return []
    executable = shutil.which("ffmpeg")
    if not executable:
        raise RuntimeError("ffmpeg is missing. Install it from https://ffmpeg.org/download.html")
    if seconds <= 0:
        points = [0.0]
    else:
        points = [seconds * (index + 1) / (count + 1) for index in range(count)]
    frames = output / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    created: list[str] = []
    for index, point in enumerate(points, start=1):
        target = frames / f"frame-{index:02d}.jpg"
        result = run(
            [
                executable,
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{point:.3f}",
                "-i",
                str(path),
                "-frames:v",
                "1",
                "-vf",
                "scale='min(1600,iw)':-2",
                "-q:v",
                "2",
                "-pix_fmt",
                "yuvj420p",
                "-y",
                str(target),
            ],
            timeout=300,
        )
        complete_jpeg = (
            target.is_file()
            and target.stat().st_size > 4
            and target.read_bytes().endswith(b"\xff\xd9")
        )
        if result.returncode or not complete_jpeg:
            message = result.stderr or "A representative frame could not be extracted."
            raise RuntimeError(message.strip())
        created.append(str(target))
    return created


def transcription_command(
    backend: str, executable: str, source: Path, output: Path, language: str | None
) -> tuple[list[str], str]:
    if backend == "mlx_whisper":
        command = [
            executable,
            str(source),
            "--model",
            "mlx-community/whisper-large-v3-turbo",
            "--output-dir",
            str(output),
            "--output-name",
            "transcript",
            "--output-format",
            "vtt",
            "--verbose",
            "False",
        ]
        if language:
            command.extend(["--language", language])
        return command, "transcript.vtt"
    command = [
        executable,
        str(source),
        "--model",
        "turbo",
        "--output_dir",
        str(output),
        "--output_format",
        "vtt",
        "--verbose",
        "False",
    ]
    if language:
        command.extend(["--language", language])
    return command, f"{source.stem}.vtt"


def transcription_backend(system: str | None = None) -> str:
    system = system or platform.system()
    if system == "Darwin" and shutil.which("mlx_whisper"):
        return "mlx_whisper"
    return "whisper"


def transcribe(path: Path, output: Path, language: str | None) -> tuple[str, str]:
    backend = transcription_backend()
    executable = shutil.which(backend)
    if not executable:
        message = (
            "No local transcription tool is available. Install Whisper from "
            "https://github.com/openai/whisper"
        )
        if platform.system() == "Darwin":
            message += (
                " or MLX Whisper from "
                "https://github.com/ml-explore/mlx-examples/tree/main/whisper"
            )
        raise RuntimeError(message)
    command, expected = transcription_command(backend, executable, path, output, language)
    result = run(command)
    target = output / expected
    if result.returncode or not target.is_file():
        raise RuntimeError((result.stderr or "Local transcription did not produce a VTT file.").strip())
    return backend, str(target)


def capture(args: argparse.Namespace) -> tuple[dict, int]:
    source = Path(args.input).expanduser().resolve()
    if not source.is_file():
        raise ValueError("The local media file does not exist.")
    output = Path(args.output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    metadata = probe(source)
    seconds = duration(metadata)
    frames: list[str] = []
    if args.frames and has_video(metadata):
        frames = extract_frames(source, output, args.frames, seconds)
    transcript_path = ""
    backend = ""
    if args.transcribe:
        backend, transcript_path = transcribe(source, output, args.language)
    receipt = {
        "source_file": str(source),
        "captured_at": now(),
        "status": "complete",
        "acquisition_method": "user_file",
        "media_status": "local",
        "duration_seconds": seconds,
        "frames": frames,
        "transcript_status": "asr_raw" if transcript_path else "not_requested",
        "transcript_path": transcript_path,
        "transcription_backend": backend,
        "metadata": metadata,
    }
    atomic_json(output / "receipt.json", receipt)
    return receipt, 0


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("input")
    value.add_argument("--output-dir", required=True)
    value.add_argument("--frames", type=int, default=0, choices=range(0, 13))
    value.add_argument("--transcribe", action="store_true")
    value.add_argument("--language", help="Optional ISO language code such as zh or en.")
    return value


def main() -> int:
    try:
        receipt, code = capture(parser().parse_args())
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "unavailable", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
