#!/usr/bin/env python3
"""Report which optional capture capabilities are usable on this computer."""

from __future__ import annotations

import argparse
import importlib.util
import json
import ntpath
import os
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
        "label": "Optional Feishu message input for Codex or Claude",
        "commands": ("lark-channel-bridge",),
        "url": "https://github.com/zarazhangrui/lark-coding-agent-bridge",
    },
}


def host_system() -> str:
    return platform.system()


def platform_support(system: str | None = None) -> str:
    system = system or host_system()
    if system == "Darwin":
        return "stable"
    if system == "Windows":
        return "beta"
    return "unsupported"


def command_path(name: str, system: str | None = None) -> str | None:
    system = system or host_system()
    found = shutil.which(name)
    if found:
        return found
    if system == "Windows":
        if not name.lower().endswith(".exe"):
            return shutil.which(f"{name}.exe")
        return None
    if system != "Darwin":
        return None
    for prefix in (Path("/opt/homebrew/bin"), Path("/usr/local/bin")):
        candidate = prefix / name
        if candidate.is_file():
            return str(candidate)
    return None


def local_asr(system: str | None = None) -> dict[str, object]:
    system = system or host_system()
    names = ("whisper",) if system == "Windows" else ("mlx_whisper", "whisper")
    commands = {
        name: command_path(name, system)
        for name in names
        if command_path(name, system)
    }
    modules = [
        name
        for name in names
        if importlib.util.find_spec(name) is not None
    ]
    available = bool(commands or modules)
    sources = ["https://github.com/openai/whisper"]
    if system == "Darwin":
        sources.append(
            "https://github.com/ml-explore/mlx-examples/tree/main/whisper"
        )
    return {
        "label": "Local speech transcription",
        "status": "ready" if available else "missing",
        "commands": commands,
        "modules": modules,
        "official_sources": sources,
        "note": (
            "Use OpenAI Whisper on Windows; MLX Whisper is for Apple silicon."
            if system == "Windows"
            else "Use only after real audio is available."
        ),
    }


def inspect_capability(
    name: str, item: dict[str, object], system: str | None = None
) -> dict[str, object]:
    required = tuple(str(value) for value in item["commands"])
    found = {command: command_path(command, system) for command in required}
    missing = [command for command, path in found.items() if not path]
    return {
        "label": item["label"],
        "status": "ready" if not missing else "missing",
        "commands": found,
        "missing": missing,
        "official_source": item["url"],
    }


def obsidian_path(
    system: str | None = None,
    environment: dict[str, str] | os._Environ[str] | None = None,
) -> str | None:
    system = system or host_system()
    environment = os.environ if environment is None else environment
    override = environment.get("CYBER_BOOKHOUSE_OBSIDIAN_APP") or environment.get(
        "CYBER_SANWEI_OBSIDIAN_APP"
    )
    if override and Path(override).expanduser().exists():
        return str(Path(override).expanduser())
    if system == "Windows":
        user_profile = environment.get("USERPROFILE") or str(Path.home())
        local = environment.get("LOCALAPPDATA") or ntpath.join(
            user_profile, "AppData", "Local"
        )
        program_files = environment.get("ProgramFiles") or r"C:\Program Files"
        candidates = (
            ntpath.join(local, "Obsidian", "Obsidian.exe"),
            ntpath.join(local, "Programs", "Obsidian", "Obsidian.exe"),
            ntpath.join(program_files, "Obsidian", "Obsidian.exe"),
        )
    else:
        candidates = ("/Applications/Obsidian.app",)
    for value in candidates:
        candidate = Path(value)
        if candidate.exists():
            return str(candidate)
    return None


def wechat_channels_skill_path(
    system: str | None = None,
    environment: dict[str, str] | os._Environ[str] | None = None,
) -> str | None:
    system = system or host_system()
    environment = os.environ if environment is None else environment
    override = environment.get("CYBER_BOOKHOUSE_WECHAT_CHANNELS_SKILL")
    if override:
        candidate = Path(override).expanduser()
        if candidate.is_dir() and (candidate / "SKILL.md").is_file():
            return str(candidate)
    home_value = (
        environment.get("USERPROFILE")
        if system == "Windows"
        else environment.get("HOME")
    )
    home = Path(home_value).expanduser() if home_value else Path.home()
    candidates = (
        home / ".codex" / "skills" / "download-wechat-channels",
        home / ".agents" / "skills" / "download-wechat-channels",
        home / ".claude" / "skills" / "download-wechat-channels",
    )
    for candidate in candidates:
        if candidate.is_dir() and (candidate / "SKILL.md").is_file():
            return str(candidate)
    return None


def report(
    system: str | None = None,
    environment: dict[str, str] | os._Environ[str] | None = None,
) -> dict[str, object]:
    system = system or host_system()
    obsidian_app = obsidian_path(system, environment)
    capabilities = {
        name: inspect_capability(name, item, system)
        for name, item in SOFTWARE.items()
    }
    capabilities["local_asr"] = local_asr(system)
    capabilities["visible_browser"] = {
        "label": "Read content visibly rendered in an authorized browser",
        "status": "host_check_required",
        "note": (
            "This is a Codex, Claude, or WorkBuddy host capability. Never replace it "
            "with automatic cookie export."
        ),
    }
    capabilities["vision_model"] = {
        "label": "Inspect real PNG or JPEG frames in the current host",
        "status": "host_check_required",
        "official_source": "https://learn.chatgpt.com/docs/image-inputs",
        "note": (
            "Test one real image in the active model and surface. Video processing "
            "uses extracted frames plus local transcription; native MP4 input is not required."
        ),
    }
    channels_skill = wechat_channels_skill_path(system, environment)
    capabilities["wechat_channels"] = {
        "label": "Authorized WeChat Channels download through Tencent Yuanbao",
        "status": "host_check_required",
        "component_status": "ready" if channels_skill else "missing",
        "component_path": channels_skill,
        "official_source": "https://yuanbao.tencent.com/",
        "requirements": [
            "Codex desktop Browser plugin",
            "user-approved full CDP access",
            "user QR login to Tencent Yuanbao",
            "one authorized real-link download test",
        ],
        "note": (
            "The public package does not rebundle a separate downloader. If the component "
            "is absent or the host checks fail, ask for an authorized local MP4."
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
            "system": system,
            "machine": platform.machine(),
            "python": platform.python_version(),
            "support_level": platform_support(system),
            "shell": "PowerShell" if system == "Windows" else "Terminal",
            "host_verification_required": system == "Windows",
        },
        "core": {
            "obsidian": obsidian_app,
            "status": "ready" if obsidian_app else "missing",
            "official_source": "https://obsidian.md/download",
        },
        "capabilities": capabilities,
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument(
        "--require",
        choices=tuple(SOFTWARE)
        + (
            "local_asr",
            "visible_browser",
            "vision_model",
            "wechat_channels",
            "public_web",
        ),
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
