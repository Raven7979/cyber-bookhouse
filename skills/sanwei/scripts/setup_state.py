#!/usr/bin/env python3
"""Track and verify the local 赛博三味书屋 onboarding process."""

from __future__ import annotations

import argparse
import json
import ntpath
import os
import platform
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VAULT_DISPLAY_NAME = "赛博三味书屋"
DEFAULT_VAULT_DIRNAME = "cyber-sanwei"
DEFAULT_DESTINATION = "obsidian"
DESTINATIONS = ("obsidian", "obsidian-feishu")
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


def host_system() -> str:
    return platform.system()


def joined(system: str, root: str | Path, *parts: str) -> Path:
    if system == "Windows":
        return Path(ntpath.join(str(root), *parts))
    return Path(root).joinpath(*parts)


def platform_locations(
    system: str | None = None,
    environment: dict[str, str] | os._Environ[str] | None = None,
    home: str | Path | None = None,
) -> dict[str, Any]:
    system = system or host_system()
    environment = os.environ if environment is None else environment
    home = Path(home) if home is not None else Path.home()
    if system == "Windows":
        user_profile = environment.get("USERPROFILE") or str(home)
        local = environment.get("LOCALAPPDATA") or ntpath.join(
            user_profile, "AppData", "Local"
        )
        roaming = environment.get("APPDATA") or ntpath.join(
            user_profile, "AppData", "Roaming"
        )
        program_files = environment.get("ProgramFiles") or r"C:\Program Files"
        windows_apps = ntpath.join(local, "Microsoft", "WindowsApps")
        applications = {
            "obsidian": (
                joined(system, local, "Obsidian", "Obsidian.exe"),
                joined(system, local, "Programs", "Obsidian", "Obsidian.exe"),
                joined(system, program_files, "Obsidian", "Obsidian.exe"),
            ),
            "workbuddy": (
                joined(system, local, "Programs", "WorkBuddy", "WorkBuddy.exe"),
                joined(system, local, "WorkBuddy", "WorkBuddy.exe"),
                joined(system, program_files, "WorkBuddy", "WorkBuddy.exe"),
            ),
            "chatgpt": (
                joined(system, windows_apps, "ChatGPT.exe"),
                joined(system, local, "Programs", "ChatGPT", "ChatGPT.exe"),
            ),
            "codex": (
                joined(system, windows_apps, "Codex.exe"),
                joined(system, local, "Programs", "Codex", "Codex.exe"),
                joined(system, program_files, "Codex", "Codex.exe"),
            ),
        }
        return {
            "config": joined(system, local, "cyber-sanwei", "config.json"),
            "data": joined(system, local, "cyber-sanwei", "data"),
            "notes": joined(system, user_profile, "Documents", DEFAULT_VAULT_DIRNAME),
            "obsidian_registry": joined(
                system, roaming, "obsidian", "obsidian.json"
            ),
            "applications": applications,
        }
    applications = {
        "obsidian": (Path("/Applications/Obsidian.app"),),
        "workbuddy": (Path("/Applications/WorkBuddy.app"),),
        "chatgpt": (Path("/Applications/ChatGPT.app"),),
        "codex": (Path("/Applications/Codex.app"),),
    }
    return {
        "config": home / ".config" / "cyber-sanwei" / "config.json",
        "data": home / ".local" / "share" / "cyber-sanwei",
        "notes": home / "Documents" / DEFAULT_VAULT_DIRNAME,
        "obsidian_registry": home
        / "Library"
        / "Application Support"
        / "obsidian"
        / "obsidian.json",
        "applications": applications,
    }


LOCATIONS = platform_locations()
DEFAULT_CONFIG = LOCATIONS["config"]
DEFAULT_DATA = LOCATIONS["data"]
DEFAULT_NOTES = LOCATIONS["notes"]
OBSIDIAN_REGISTRY = LOCATIONS["obsidian_registry"]
APPLICATIONS = LOCATIONS["applications"]
MARKABLE_STEPS = (
    "vault_registered",
    "desktop_test",
    "mobile_connected",
    "mobile_test",
    "channel_connected",
    "channel_test",
)
CORE_STEPS = (
    "agent_selected",
    "software",
    "vault_created",
    "vault_registered",
    "desktop_test",
    "mobile_connected",
    "mobile_test",
)
READY_COMMANDS = (
    {
        "command": "同步笔记：<链接或文件>",
        "purpose": "视频总结、逐字稿和必要的翻译；图文总结，适合学习、记录和留档",
    },
    {
        "command": "蒸馏笔记：<链接或文件>",
        "purpose": "详细结构分析，重点适合短片拉片",
    },
    {
        "command": "详细拆解：<链接或文件>",
        "purpose": "完整包含同步笔记和蒸馏笔记",
    },
    {"command": "检查书屋", "purpose": "检查连接、依赖和本地笔记路径"},
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


def executable(name: str, system: str | None = None) -> str | None:
    system = system or host_system()
    found = shutil.which(name)
    if found:
        return found
    if system == "Windows" and not name.lower().endswith(".exe"):
        found = shutil.which(f"{name}.exe")
        if found:
            return found
        return None
    if system != "Darwin":
        return None
    for prefix in (Path("/opt/homebrew/bin"), Path("/usr/local/bin")):
        candidate = prefix / name
        if candidate.is_file():
            return str(candidate)
    return None


def platform_support(system: str | None = None) -> str:
    system = system or host_system()
    if system == "Darwin":
        return "stable"
    if system == "Windows":
        return "beta"
    return "unsupported"


APPLICATION_ENV = {
    "obsidian": "CYBER_SANWEI_OBSIDIAN_APP",
    "workbuddy": "CYBER_SANWEI_WORKBUDDY_APP",
    "chatgpt": "CYBER_SANWEI_CHATGPT_APP",
    "codex": "CYBER_SANWEI_CODEX_APP",
}


def find_application(
    name: str,
    system: str | None = None,
    environment: dict[str, str] | os._Environ[str] | None = None,
    locations: dict[str, Any] | None = None,
) -> str | None:
    system = system or host_system()
    environment = os.environ if environment is None else environment
    override = environment.get(APPLICATION_ENV[name])
    if override:
        candidate = Path(override).expanduser()
        if candidate.exists():
            return str(candidate)
    locations = locations or platform_locations(system, environment)
    for candidate in locations["applications"][name]:
        if candidate.exists():
            return str(candidate)
    if system == "Windows":
        return executable(name, system)
    return None


def configured_notes_root(
    fallback: Path = DEFAULT_NOTES,
    environment: dict[str, str] | os._Environ[str] | None = None,
    selected_config: Path | None = None,
) -> Path:
    environment = os.environ if environment is None else environment
    selected_config = selected_config or Path(
        environment.get("CYBER_SANWEI_CONFIG") or DEFAULT_CONFIG
    )
    config = read_json(selected_config)
    value = config.get("notes_root")
    return Path(str(value)).expanduser() if value else fallback


def vault_registered(notes_root: Path, registry_path: Path | None = None) -> bool:
    registry_path = registry_path or resolve_path(
        "CYBER_SANWEI_OBSIDIAN_REGISTRY", OBSIDIAN_REGISTRY
    )
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


def detected(
    system: str | None = None,
    environment: dict[str, str] | os._Environ[str] | None = None,
    home: str | Path | None = None,
) -> dict[str, Any]:
    system = system or host_system()
    environment = os.environ if environment is None else environment
    locations = platform_locations(system, environment, home)
    selected_config = Path(
        environment.get("CYBER_SANWEI_CONFIG") or locations["config"]
    ).expanduser()
    selected_data = Path(
        environment.get("CYBER_SANWEI_DATA") or locations["data"]
    ).expanduser()
    notes_root = configured_notes_root(
        locations["notes"], environment, selected_config
    )
    registry_path = Path(
        environment.get("CYBER_SANWEI_OBSIDIAN_REGISTRY")
        or locations["obsidian_registry"]
    ).expanduser()
    codex_cli = executable("codex", system)
    chatgpt_app = find_application("chatgpt", system, environment, locations)
    codex_app = find_application("codex", system, environment, locations)
    codex_desktop = chatgpt_app or codex_app
    obsidian_app = find_application("obsidian", system, environment, locations)
    workbuddy_app = find_application("workbuddy", system, environment, locations)
    return {
        "platform": {
            "system": system,
            "machine": platform.machine(),
            "python": platform.python_version(),
            "support_level": platform_support(system),
            "shell": "PowerShell" if system == "Windows" else "Terminal",
            "host_verification_required": system == "Windows",
        },
        "software": {
            "obsidian": obsidian_app,
            "codex": codex_desktop or codex_cli,
            "codex_desktop": codex_desktop,
            "codex_cli": codex_cli,
            "workbuddy": workbuddy_app,
            "node": executable("node", system),
            "npm": executable("npm", system),
            "lark_channel_bridge": executable("lark-channel-bridge", system),
        },
        "paths": {
            "config": str(selected_config),
            "state": str(joined(system, selected_data, "setup.json")),
            "notes_root": str(notes_root),
        },
        "vault": {
            "display_name": VAULT_DISPLAY_NAME,
            "directory_name": notes_root.name,
            "directory_exists": notes_root.is_dir(),
            "welcome_note_exists": (notes_root / "欢迎来到赛博三味书屋.md").is_file(),
            "registered_in_obsidian": vault_registered(notes_root, registry_path),
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
            "> 同步笔记：<文章、视频或播客链接>",
            "",
            "三种方式：",
            "",
            "- 同步笔记：总结、逐字稿、必要的翻译，适合学习和留档。",
            "- 蒸馏笔记：详细结构分析，重点适合短片拉片。",
            "- 详细拆解：同时包含前两种结果。",
            "",
            "Markdown 文件是原件；Obsidian 用于阅读、搜索和整理。",
            "",
        )
    )


def validate_agent_channel(agent: str, channel: str) -> None:
    if agent == "codex" and channel == "wechat":
        raise ValueError(
            "WeChat is supported only through WorkBuddy in this release. "
            "Choose desktop or feishu for Codex."
        )


def apply_channel_state(
    state: dict[str, Any], channel: str
) -> dict[str, Any]:
    state["channel"] = channel
    state["steps"]["channel_selected"] = {
        "status": "complete",
        "evidence": channel,
        "updated_at": now(),
    }
    if channel == "desktop":
        evidence = "no additional Feishu or WeChat connector requested"
        for step in ("channel_connected", "channel_test"):
            state["steps"][step] = {
                "status": "complete",
                "evidence": evidence,
                "updated_at": now(),
            }
    else:
        for step in ("channel_connected", "channel_test"):
            state["steps"][step] = {
                "status": "pending",
                "evidence": "",
                "updated_at": "",
            }
    return state


def command_doctor(_: argparse.Namespace) -> int:
    report = detected()
    report["setup"] = normalize_state(read_json(state_path())) if state_path().is_file() else {}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def command_init(args: argparse.Namespace) -> int:
    validate_agent_channel(args.agent, args.channel)
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
    destination = (
        DEFAULT_DESTINATION
        if route_changed
        else str(previous_config.get("destination") or DEFAULT_DESTINATION)
    )

    config = {
        "version": 1,
        "agent": args.agent,
        "channel": args.channel,
        "destination": destination,
        "vault_display_name": VAULT_DISPLAY_NAME,
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
            "destination": destination,
            "created_at": previous_state.get("created_at") or now(),
            "updated_at": now(),
        }
    )
    state["steps"]["agent_selected"] = {
        "status": "complete",
        "evidence": args.agent,
        "updated_at": now(),
    }
    state = apply_channel_state(state, args.channel)
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
    state = normalize_state(state)
    atomic_json(state_path(), state)
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


def command_set_channel(args: argparse.Namespace) -> int:
    config = read_json(config_path())
    state = normalize_state(read_json(state_path()))
    agent = str(state.get("agent") or config.get("agent") or "")
    if not agent:
        raise RuntimeError("Run init before selecting an optional input route.")
    validate_agent_channel(agent, args.channel)

    incomplete = [
        step
        for step in CORE_STEPS
        if state["steps"][step]["status"] != "complete"
    ]
    if incomplete:
        raise RuntimeError(
            "Finish core setup before selecting Feishu or WeChat. "
            f"Incomplete steps: {', '.join(incomplete)}"
        )

    config["agent"] = agent
    config["channel"] = args.channel
    config["updated_at"] = now()
    atomic_json(config_path(), config)

    state = apply_channel_state(state, args.channel)
    state["updated_at"] = now()
    state = normalize_state(state)
    atomic_json(state_path(), state)
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


def command_set_destination(args: argparse.Namespace) -> int:
    config = read_json(config_path())
    state = normalize_state(read_json(state_path()))
    agent = str(state.get("agent") or config.get("agent") or "")
    if not agent:
        raise RuntimeError("Run init before selecting an output destination.")
    if args.destination == "obsidian-feishu" and agent != "codex":
        raise ValueError(
            "Feishu Docs output is documented for Codex only in this release."
        )

    incomplete = [
        step
        for step in CORE_STEPS
        if state["steps"][step]["status"] != "complete"
    ]
    if incomplete:
        raise RuntimeError(
            "Finish core setup before selecting an output destination. "
            f"Incomplete steps: {', '.join(incomplete)}"
        )
    if args.destination == "obsidian-feishu" and not args.evidence.strip():
        raise ValueError(
            "Feishu Docs output requires evidence from a created and read-back test document."
        )

    evidence = args.evidence.strip() or "local Obsidian only"
    config["agent"] = agent
    config["destination"] = args.destination
    config["destination_evidence"] = evidence
    config["updated_at"] = now()
    atomic_json(config_path(), config)

    state["destination"] = args.destination
    state["destination_evidence"] = evidence
    state["updated_at"] = now()
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
        "destination": state.get("destination")
        or read_json(config_path()).get("destination")
        or DEFAULT_DESTINATION,
        "destination_evidence": state.get("destination_evidence")
        or read_json(config_path()).get("destination_evidence")
        or "",
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
        "ready_commands": list(READY_COMMANDS) if state.get("complete") else [],
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

    set_channel = subcommands.add_parser(
        "set-channel",
        help="Select an optional input route after core setup is complete.",
    )
    set_channel.add_argument(
        "--channel", choices=("desktop", "feishu", "wechat"), required=True
    )
    set_channel.set_defaults(func=command_set_channel)

    set_destination = subcommands.add_parser(
        "set-destination",
        help="Select the output destination after core setup is complete.",
    )
    set_destination.add_argument(
        "--destination", choices=DESTINATIONS, required=True
    )
    set_destination.add_argument("--evidence", default="")
    set_destination.set_defaults(func=command_set_destination)

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
