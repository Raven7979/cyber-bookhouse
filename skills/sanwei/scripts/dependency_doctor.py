#!/usr/bin/env python3
"""Report which optional capture capabilities are usable on this computer."""

from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import shutil
from pathlib import Path


SOFTWARE = {
    "youtube": {
        "label": "YouTube public metadata and subtitles",
        "commands": ("yt-dlp",),
        "url": "https://github.com/yt-dlp/yt-dlp#installation",
    },
    "media": {
        "label": "Local audio and video processing",
        "commands": ("ffmpeg", "ffprobe"),
        "url": "https://ffmpeg.org/download.html",
    },
    "feishu_docs": {
        "label": "Optional Feishu Docs output",
        "commands": ("lark-cli",),
        "url": "https://github.com/larksuite/cli",
    },
    "feishu_input": {
        "label": "Optional Feishu message input for Codex",
        "commands": ("lark-channel-bridge",),
        "url": "https://github.com/zarazhangrui/lark-coding-agent-bridge",
    },
}


def command_path(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    for prefix in (Path("/opt/homebrew/bin"), Path("/usr/local/bin")):
        candidate = prefix / name
        if candidate.is_file():
            return str(candidate)
    return None


def local_asr() -> dict[str, object]:
    commands = {
        name: command_path(name)
        for name in ("mlx_whisper", "whisper")
        if command_path(name)
    }
    modules = [
        name
        for name in ("mlx_whisper", "whisper")
        if importlib.util.find_spec(name) is not None
    ]
    available = bool(commands or modules)
    return {
        "label": "Local speech transcription",
        "status": "ready" if available else "missing",
        "commands": commands,
        "modules": modules,
        "official_sources": [
            "https://github.com/openai/whisper",
            "https://github.com/ml-explore/mlx-examples/tree/main/whisper",
        ],
        "note": "Use only after real audio is available.",
    }


def inspect_capability(name: str, item: dict[str, object]) -> dict[str, object]:
    required = tuple(str(value) for value in item["commands"])
    found = {command: command_path(command) for command in required}
    missing = [command for command, path in found.items() if not path]
    return {
        "label": item["label"],
        "status": "ready" if not missing else "missing",
        "commands": found,
        "missing": missing,
        "official_source": item["url"],
    }


def report() -> dict[str, object]:
    obsidian_app = Path("/Applications/Obsidian.app")
    capabilities = {
        name: inspect_capability(name, item) for name, item in SOFTWARE.items()
    }
    capabilities["local_asr"] = local_asr()
    capabilities["visible_browser"] = {
        "label": "Read content visibly rendered in an authorized browser",
        "status": "host_check_required",
        "note": (
            "This is a Codex or WorkBuddy host capability. Never replace it "
            "with automatic cookie export."
        ),
    }
    capabilities["public_web"] = {
        "label": "Public HTML and plain-text pages",
        "status": "ready",
        "adapter": "scripts/web_capture.py",
        "note": "Dynamic, logged-in, or paywalled pages still require a host check or export.",
    }
    return {
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "core": {
            "obsidian": str(obsidian_app) if obsidian_app.is_dir() else None,
            "status": "ready" if obsidian_app.is_dir() else "missing",
            "official_source": "https://obsidian.md/download",
        },
        "capabilities": capabilities,
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument(
        "--require", choices=tuple(SOFTWARE) + ("local_asr", "public_web")
    )
    return value


def main() -> int:
    args = parser().parse_args()
    payload = report()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.require:
        selected = payload["capabilities"][args.require]
        return 0 if selected["status"] == "ready" else 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
