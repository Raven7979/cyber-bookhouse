#!/usr/bin/env python3
"""Acquire YouTube metadata and subtitles without reading browser cookies."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import Request, urlopen


BOT_CHECK_MARKERS = (
    "sign in to confirm you’re not a bot",
    "sign in to confirm you're not a bot",
    "confirm you’re not a bot",
    "confirm you're not a bot",
)


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


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(text.rstrip() + "\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def video_id(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower().split(":", 1)[0]
    if host in {"youtu.be", "www.youtu.be"}:
        value = parsed.path.strip("/").split("/", 1)[0]
    elif host.endswith("youtube.com"):
        if parsed.path == "/watch":
            value = (parse_qs(parsed.query).get("v") or [""])[0]
        else:
            parts = parsed.path.strip("/").split("/")
            value = parts[1] if len(parts) > 1 and parts[0] in {"shorts", "embed"} else ""
    else:
        value = ""
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,20}", value):
        raise ValueError("The URL does not contain a recognizable YouTube video ID.")
    return value


def oembed_metadata(url: str) -> dict:
    endpoint = (
        "https://www.youtube.com/oembed?format=json&url="
        + quote(url, safe="")
    )
    request = Request(endpoint, headers={"User-Agent": "cyber-bookhouse/0.2.1"})
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read(2 * 1024 * 1024).decode("utf-8"))
    except Exception:
        return {}
    return {
        "title": str(payload.get("title") or ""),
        "author": str(payload.get("author_name") or ""),
        "author_url": str(payload.get("author_url") or ""),
        "thumbnail_url": str(payload.get("thumbnail_url") or ""),
        "provider": str(payload.get("provider_name") or "YouTube"),
    }


def parse_timestamp(value: str) -> float:
    parts = value.replace(",", ".").split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
    except ValueError:
        pass
    return 0.0


def stamp(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


def vtt_to_text(path: Path) -> str:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    output: list[str] = []
    previous = ""
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if "-->" not in line:
            index += 1
            continue
        start = parse_timestamp(line.split("-->", 1)[0].strip().split()[0])
        index += 1
        words: list[str] = []
        while index < len(lines) and lines[index].strip():
            cleaned = re.sub(r"<[^>]+>", "", lines[index]).strip()
            cleaned = re.sub(r"\s+", " ", html.unescape(cleaned))
            if cleaned:
                words.append(cleaned)
            index += 1
        text = re.sub(r"\s+", " ", " ".join(words)).strip()
        if text and text != previous:
            output.append(f"[{stamp(start)}] {text}")
            previous = text
        index += 1
    return "\n".join(output)


def classify_error(text: str) -> str:
    lowered = text.lower()
    if any(marker in lowered for marker in BOT_CHECK_MARKERS):
        return "youtube_bot_check"
    if "private video" in lowered:
        return "private_video"
    if "video unavailable" in lowered:
        return "video_unavailable"
    return "extractor_error"


def public_error(reason: str, detail: str) -> str:
    if reason == "youtube_bot_check":
        return (
            "YouTube required a human verification session. Automatic browser "
            "cookie export was not attempted."
        )
    return detail[-1200:]


def run(command: list[str], timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def select_metadata(raw: dict, url: str) -> dict:
    return {
        "id": str(raw.get("id") or video_id(url)),
        "title": str(raw.get("title") or ""),
        "author": str(raw.get("channel") or raw.get("uploader") or ""),
        "channel_url": str(raw.get("channel_url") or raw.get("uploader_url") or ""),
        "description": str(raw.get("description") or ""),
        "duration": raw.get("duration"),
        "upload_date": str(raw.get("upload_date") or ""),
        "webpage_url": str(raw.get("webpage_url") or url),
    }


def staged_transcript(path: Path, output: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if len(text) < 40:
        raise ValueError("The staged transcript is too short to verify.")
    target = output / "transcript.txt"
    atomic_text(target, text)
    return {
        "status": "complete",
        "transcript_status": "official_visible_text",
        "acquisition_method": "authorized_browser",
        "transcript_path": str(target),
    }


def capture(args: argparse.Namespace) -> tuple[dict, int]:
    output = Path(args.output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    identifier = video_id(args.url)
    metadata = oembed_metadata(args.url)
    metadata.update({"id": identifier, "source_url": args.url})

    if args.staged_transcript:
        staged = staged_transcript(Path(args.staged_transcript).expanduser(), output)
        receipt = {
            "source_url": args.url,
            "captured_at": now(),
            "metadata": metadata,
            **staged,
        }
        atomic_json(output / "metadata.json", metadata)
        atomic_json(output / "receipt.json", receipt)
        return receipt, 0

    executable = shutil.which("yt-dlp")
    if not executable:
        receipt = {
            "source_url": args.url,
            "captured_at": now(),
            "status": "dependency_missing",
            "reason": "yt_dlp_missing",
            "metadata": metadata,
            "official_source": "https://github.com/yt-dlp/yt-dlp#installation",
        }
        atomic_json(output / "metadata.json", metadata)
        atomic_json(output / "receipt.json", receipt)
        return receipt, 2

    base = [executable, "--no-playlist"]
    if shutil.which("node"):
        base.extend(["--js-runtimes", "node"])
    info_result = run(
        [*base, "--skip-download", "--dump-single-json", args.url], timeout=180
    )
    if info_result.returncode != 0:
        detail = (info_result.stderr or info_result.stdout).strip()
        reason = classify_error(detail)
        receipt = {
            "source_url": args.url,
            "captured_at": now(),
            "status": "authorization_required" if reason == "youtube_bot_check" else "unavailable",
            "reason": reason,
            "metadata": metadata,
            "transcript_status": "unavailable",
            "next_actions": [
                "authorize_visible_browser_transcript",
                "provide_subtitle_or_media_file",
            ],
            "error": public_error(reason, detail),
        }
        atomic_json(output / "metadata.json", metadata)
        atomic_json(output / "receipt.json", receipt)
        return receipt, 3

    raw = json.loads(info_result.stdout)
    metadata = select_metadata(raw, args.url)
    subtitle_template = str(output / "subtitle.%(language)s.%(ext)s")
    subtitle_result = run(
        [
            *base,
            "--skip-download",
            "--write-sub",
            "--write-auto-sub",
            "--sub-langs",
            "zh-Hans,zh-Hant,zh,en.*",
            "--sub-format",
            "vtt",
            "-o",
            subtitle_template,
            args.url,
        ],
        timeout=300,
    )
    transcript_path = ""
    for subtitle in sorted(output.glob("subtitle.*.vtt")):
        text = vtt_to_text(subtitle)
        if text:
            target = output / "transcript.txt"
            atomic_text(target, text)
            transcript_path = str(target)
            break
    status = "complete" if transcript_path else "partial"
    receipt = {
        "source_url": args.url,
        "captured_at": now(),
        "status": status,
        "reason": "" if transcript_path else "subtitle_unavailable",
        "metadata": metadata,
        "transcript_status": "source_subtitles" if transcript_path else "unavailable",
        "transcript_path": transcript_path,
        "subtitle_command_status": subtitle_result.returncode,
        "next_actions": []
        if transcript_path
        else [
            "authorize_visible_browser_transcript",
            "provide_subtitle_or_media_file",
        ],
    }
    atomic_json(output / "metadata.json", metadata)
    atomic_json(output / "receipt.json", receipt)
    return receipt, 0


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("url")
    value.add_argument("--output-dir", required=True)
    value.add_argument(
        "--staged-transcript",
        help="Visible transcript text exported from an explicitly authorized browser page.",
    )
    return value


def main() -> int:
    try:
        receipt, code = capture(parser().parse_args())
    except (OSError, ValueError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
