#!/usr/bin/env python3
"""Track and verify the local 赛博三味书屋 onboarding process."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = Path.home() / ".config" / "cyber-sanwei" / "config.json"
DEFAULT_DATA = Path.home() / ".local" / "share" / "cyber-sanwei"
DEFAULT_NOTES = Path.home() / "Documents" / "赛博三味书屋"
OBSIDIAN_APP = Path("/Applications/Obsidian.app")
WORKBUDDY_APP = Path("/Applications/WorkBuddy.app")
CHATGPT_APP = Path("/Applications/ChatGPT.app")
CODEX_APP = Path("/Applications/Codex.app")
OBSIDIAN_REGISTRY = (
    Path.home() / "Library" / "Application Support" / "obsidian" / "obsidian.json"
)
STEPS = (
    "agent_selected",
    "channel_selected",
    "software",
    "vault_created",
    "vault_registered",
    "desktop_test",
    "mobile_connected",
    "mobile_test",
    "channel_connected",
    "channel_test",
)
MARKABLE_STEPS = (
    "vault_registered",
    "desktop_test",
    "mobile_connected",
    "mobile_test",
    "channel_connected",
    "channel_test",
)


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def resolve_path(env_name: str, fallback: Path) -> Path:
    value = os.environ.get(env_name)
    return Path(value).expanduser() if value else fallback


def config_path() -> Path:
    return resolve_path("CYBER_SANWEI_CONFIG", DEFAULT_CONFIG)


def data_root() -> Path:
    return resolve_path("CYBER_SANWEI_DATA", DEFAULT_DATA)


def state_path() -> Path:
    return data_root() / "setup.json"


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        temporary_path = Path(temporary)
        if temporary_path.exists():
            temporary_path.unlink()


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def executable(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    for prefix in (Path("/opt/homebrew/bin"), Path("/usr/local/bin")):
        candidate = prefix / name
        if candidate.is_file():
            return str(candidate)
    return None


def configured_notes_root() -> Path:
    config = read_json(config_path())
    value = config.get("notes_root")
    return Path(str(value)).expanduser() if value else DEFAULT_NOTES


def vault_registered(notes_root: Path) -> bool:
    registry_path = resolve_path("CYBER_SANWEI_OBSIDIAN_REGISTRY", OBSIDIAN_REGISTRY)
    try:
        registry = read_json(registry_path)
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    vaults = registry.get("vaults")
    if not isinstance(vaults, dict):
        return False
    expected = str(notes_root.expanduser().resolve())
    for item in vaults.values():
        if not isinstance(item, dict) or not item.get("path"):
            continue
        if str(Path(str(item["path"])).expanduser().resolve()) == expected:
            return True
    return False


def detected() -> dict[str, Any]:
    notes_root = configured_notes_root()
    codex_cli = executable("codex")
    codex_desktop = next(
        (
            str(application)
            for application in (CHATGPT_APP, CODEX_APP)
            if application.is_dir()
        ),
        None,
    )
    return {
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "software": {
            "obsidian": str(OBSIDIAN_APP) if OBSIDIAN_APP.is_dir() else None,
            "codex": codex_desktop or codex_cli,
            "codex_desktop": codex_desktop,
            "codex_cli": codex_cli,
            "workbuddy": str(WORKBUDDY_APP) if WORKBUDDY_APP.is_dir() else None,
            "node": executable("node"),
            "npm": executable("npm"),
            "lark_channel_bridge": executable("lark-channel-bridge"),
        },
        "paths": {
            "config": str(config_path()),
            "state": str(state_path()),
            "notes_root": str(notes_root),
        },
        "vault": {
            "directory_exists": notes_root.is_dir(),
            "welcome_note_exists": (notes_root / "欢迎来到赛博三味书屋.md").is_file(),
            "registered_in_obsidian": vault_registered(notes_root),
        },
    }


def default_steps() -> dict[str, dict[str, str]]:
    return {
        step: {"status": "pending", "evidence": "", "updated_at": ""}
        for step in STEPS
    }


def normalize_state(state: dict[str, Any]) -> dict[str, Any]:
    steps = state.get("steps")
    if not isinstance(steps, dict):
        steps = {}
    normalized = default_steps()
    for key in normalized:
        item = steps.get(key)
        if isinstance(item, dict):
            normalized[key] = {
                "status": str(item.get("status") or "pending"),
                "evidence": str(item.get("evidence") or ""),
                "updated_at": str(item.get("updated_at") or ""),
            }
    state["steps"] = normalized
    state["complete"] = all(
        normalized[key]["status"] == "complete" for key in STEPS
    )
    return state


def welcome_text() -> str:
    return "\n".join(
        (
            "# 欢迎来到赛博三味书屋",
            "",
            "这里是电脑、手机和 Obsidian 共用的本地知识库。",
            "",
            "试着对 Codex、ChatGPT 手机端或 WorkBuddy 说：",
            "",
            "> 收进书屋：https://example.com",
            "",
            "Markdown 文件是原件；Obsidian 用于阅读、搜索和整理。",
            "",
        )
    )


def command_doctor(_: argparse.Namespace) -> int:
    report = detected()
    report["setup"] = normalize_state(read_json(state_path())) if state_path().is_file() else {}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def command_init(args: argparse.Namespace) -> int:
    if args.agent == "codex" and args.channel == "wechat":
        raise ValueError(
            "WeChat is supported only through WorkBuddy. "
            "Choose --channel desktop or feishu for Codex."
        )
    notes_root = Path(args.notes_root).expanduser() if args.notes_root else DEFAULT_NOTES
    notes_root.mkdir(parents=True, exist_ok=True)
    (notes_root / ".obsidian").mkdir(exist_ok=True)
    welcome = notes_root / "欢迎来到赛博三味书屋.md"
    if not welcome.exists():
        welcome.write_text(welcome_text(), encoding="utf-8")

    previous_config = read_json(config_path())
    previous_state = normalize_state(read_json(state_path()))
    route_changed = (
        previous_state.get("agent") != args.agent
        or previous_state.get("channel") != args.channel
        or previous_config.get("notes_root") != str(notes_root.resolve())
    )

    config = {
        "version": 1,
        "agent": args.agent,
        "channel": args.channel,
        "notes_root": str(notes_root.resolve()),
        "created_at": now(),
    }
    if previous_config.get("created_at"):
        config["created_at"] = previous_config["created_at"]
    config["updated_at"] = now()
    atomic_json(config_path(), config)

    report = detected()
    software = report["software"]
    selected_present = bool(software[args.agent])
    state = normalize_state({}) if route_changed else previous_state
    state.update(
        {
            "version": 1,
            "agent": args.agent,
            "channel": args.channel,
            "created_at": previous_state.get("created_at") or now(),
            "updated_at": now(),
        }
    )
    state["steps"]["agent_selected"] = {
        "status": "complete",
        "evidence": args.agent,
        "updated_at": now(),
    }
    state["steps"]["channel_selected"] = {
        "status": "complete",
        "evidence": args.channel,
        "updated_at": now(),
    }
    state["steps"]["software"] = {
        "status": "complete" if selected_present and bool(software["obsidian"]) else "pending",
        "evidence": "desktop agent and Obsidian detected"
        if selected_present and bool(software["obsidian"])
        else "install the selected desktop agent and Obsidian",
        "updated_at": now(),
    }
    state["steps"]["vault_created"] = {
        "status": "complete",
        "evidence": str(notes_root.resolve()),
        "updated_at": now(),
    }
    if report["vault"]["registered_in_obsidian"]:
        state["steps"]["vault_registered"] = {
            "status": "complete",
            "evidence": str(notes_root.resolve()),
            "updated_at": now(),
        }
    if args.channel == "desktop":
        state["steps"]["channel_connected"] = {
            "status": "complete",
            "evidence": "no additional Feishu or WeChat connector requested",
            "updated_at": now(),
        }
        state["steps"]["channel_test"] = {
            "status": "complete",
            "evidence": "no additional Feishu or WeChat connector requested",
            "updated_at": now(),
        }
    state = normalize_state(state)
    atomic_json(state_path(), state)
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


def command_mark(args: argparse.Namespace) -> int:
    state = normalize_state(read_json(state_path()))
    if not state.get("agent"):
        raise RuntimeError("Run init before marking onboarding steps.")
    if args.status == "complete" and not args.evidence.strip():
        raise ValueError("Completed steps require non-empty evidence.")
    state["steps"][args.step] = {
        "status": args.status,
        "evidence": args.evidence.strip(),
        "updated_at": now(),
    }
    state["updated_at"] = now()
    state = normalize_state(state)
    atomic_json(state_path(), state)
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


def command_status(_: argparse.Namespace) -> int:
    report = detected()
    state = normalize_state(read_json(state_path()))
    if state.get("steps"):
        if report["vault"]["registered_in_obsidian"]:
            state["steps"]["vault_registered"] = {
                "status": "complete",
                "evidence": report["paths"]["notes_root"],
                "updated_at": now(),
            }
        state = normalize_state(state)
        if state_path().is_file():
            atomic_json(state_path(), state)
    output = {
        "complete": bool(state.get("complete")),
        "agent": state.get("agent"),
        "channel": state.get("channel"),
        "notes_root": report["paths"]["notes_root"],
        "steps": state.get("steps", default_steps()),
        "next_step": next(
            (
                key
                for key in STEPS
                if state.get("steps", {}).get(key, {}).get("status") != "complete"
            ),
            None,
        ),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["complete"] else 2


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    subcommands = root.add_subparsers(dest="command", required=True)

    doctor = subcommands.add_parser("doctor", help="Detect local readiness.")
    doctor.set_defaults(func=command_doctor)

    init = subcommands.add_parser("init", help="Create config and local vault.")
    init.add_argument("--agent", choices=("codex", "workbuddy"), required=True)
    init.add_argument(
        "--channel", choices=("desktop", "feishu", "wechat"), required=True
    )
    init.add_argument("--notes-root")
    init.set_defaults(func=command_init)

    mark = subcommands.add_parser("mark", help="Record verified onboarding evidence.")
    mark.add_argument("--step", choices=MARKABLE_STEPS, required=True)
    mark.add_argument(
        "--status", choices=("pending", "complete", "blocked"), required=True
    )
    mark.add_argument("--evidence", default="")
    mark.set_defaults(func=command_mark)

    status = subcommands.add_parser("status", help="Show progress and next step.")
    status.set_defaults(func=command_status)
    return root


def main() -> int:
    try:
        args = parser().parse_args()
        return args.func(args)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
