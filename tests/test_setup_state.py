from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "sanwei"
    / "scripts"
    / "setup_state.py"
)
SPEC = importlib.util.spec_from_file_location("setup_state", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SetupStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.environment = mock.patch.dict(
            os.environ,
            {
                "CYBER_SANWEI_CONFIG": str(self.root / "config.json"),
                "CYBER_SANWEI_DATA": str(self.root / "data"),
                "CYBER_SANWEI_OBSIDIAN_REGISTRY": str(
                    self.root / "obsidian.json"
                ),
            },
            clear=False,
        )
        self.environment.start()

    def tearDown(self) -> None:
        self.environment.stop()
        self.temporary.cleanup()

    def test_atomic_json_round_trip(self) -> None:
        target = self.root / "nested" / "value.json"
        MODULE.atomic_json(target, {"name": "赛博书屋"})
        self.assertEqual(MODULE.read_json(target)["name"], "赛博书屋")

    def test_default_new_vault_uses_ascii_directory_name(self) -> None:
        self.assertEqual(MODULE.DEFAULT_VAULT_DIRNAME, "cyber-sanwei")
        self.assertTrue(MODULE.DEFAULT_VAULT_DIRNAME.isascii())
        self.assertEqual(MODULE.VAULT_DISPLAY_NAME, "赛博书屋")

    def test_windows_locations_use_appdata_and_ascii_vault(self) -> None:
        environment = {
            "USERPROFILE": r"C:\Users\Demo",
            "LOCALAPPDATA": r"C:\Users\Demo\AppData\Local",
            "APPDATA": r"C:\Users\Demo\AppData\Roaming",
            "ProgramFiles": r"C:\Program Files",
        }
        locations = MODULE.platform_locations(
            "Windows", environment, r"C:\Users\Demo"
        )
        self.assertEqual(
            str(locations["config"]),
            r"C:\Users\Demo\AppData\Local\cyber-sanwei\config.json",
        )
        self.assertEqual(
            str(locations["notes"]),
            r"C:\Users\Demo\Documents\cyber-sanwei",
        )
        self.assertEqual(
            str(locations["obsidian_registry"]),
            r"C:\Users\Demo\AppData\Roaming\obsidian\obsidian.json",
        )
        self.assertTrue(
            all(
                str(path).lower().endswith(".exe")
                for candidates in locations["applications"].values()
                for path in candidates
            )
        )

    def test_platform_support_is_explicit(self) -> None:
        self.assertEqual(MODULE.platform_support("Darwin"), "stable")
        self.assertEqual(MODULE.platform_support("Windows"), "beta")
        self.assertEqual(MODULE.platform_support("Linux"), "unsupported")

    def test_windows_detection_reports_powershell_and_native_state_path(self) -> None:
        environment = {
            "USERPROFILE": r"C:\Users\Demo",
            "LOCALAPPDATA": r"C:\Users\Demo\AppData\Local",
            "APPDATA": r"C:\Users\Demo\AppData\Roaming",
            "ProgramFiles": r"C:\Program Files",
        }
        payload = MODULE.detected("Windows", environment, r"C:\Users\Demo")
        self.assertEqual(payload["platform"]["shell"], "PowerShell")
        self.assertTrue(payload["platform"]["host_verification_required"])
        self.assertEqual(
            payload["paths"]["state"],
            r"C:\Users\Demo\AppData\Local\cyber-sanwei\data\setup.json",
        )

    def test_application_override_supports_non_default_install_path(self) -> None:
        application = self.root / "Obsidian.exe"
        application.write_bytes(b"")
        environment = {"CYBER_SANWEI_OBSIDIAN_APP": str(application)}
        self.assertEqual(
            MODULE.find_application("obsidian", "Windows", environment),
            str(application),
        )

    def test_init_without_custom_path_uses_ascii_default(self) -> None:
        default_notes = self.root / MODULE.DEFAULT_VAULT_DIRNAME
        args = type(
            "Args",
            (),
            {
                "agent": "workbuddy",
                "channel": "desktop",
                "notes_root": None,
            },
        )()
        with (
            mock.patch.object(MODULE, "DEFAULT_NOTES", default_notes),
            mock.patch.object(
                MODULE, "detected", return_value=self.fake_detection("workbuddy")
            ),
        ):
            MODULE.command_init(args)
        config = MODULE.read_json(MODULE.config_path())
        self.assertEqual(Path(config["notes_root"]), default_notes.resolve())
        self.assertEqual(config["vault_display_name"], "赛博书屋")
        self.assertTrue((default_notes / "欢迎来到赛博书屋.md").is_file())

    def test_custom_existing_chinese_vault_path_is_preserved(self) -> None:
        args = self.init_args("workbuddy", "desktop", "已有中文仓库")
        with mock.patch.object(
            MODULE, "detected", return_value=self.fake_detection("workbuddy")
        ):
            MODULE.command_init(args)
        config = MODULE.read_json(MODULE.config_path())
        self.assertEqual(
            Path(config["notes_root"]), (self.root / "已有中文仓库").resolve()
        )

    def test_vault_registration_matches_resolved_path(self) -> None:
        notes = self.root / "notes"
        notes.mkdir()
        registry = {"vaults": {"sample": {"path": str(notes)}}}
        (self.root / "obsidian.json").write_text(
            json.dumps(registry), encoding="utf-8"
        )
        self.assertTrue(MODULE.vault_registered(notes))

    def test_complete_requires_every_step(self) -> None:
        state = {"steps": MODULE.default_steps()}
        for step in MODULE.STEPS:
            state["steps"][step]["status"] = "complete"
        state["steps"]["channel_test"]["status"] = "pending"
        self.assertFalse(MODULE.normalize_state(state)["complete"])
        state["steps"]["channel_test"]["status"] = "complete"
        self.assertTrue(MODULE.normalize_state(state)["complete"])

    def test_ready_commands_explain_all_three_modes(self) -> None:
        commands = {item["command"]: item["purpose"] for item in MODULE.READY_COMMANDS}
        self.assertIn("同步笔记：<链接或文件>", commands)
        self.assertIn("蒸馏笔记：<链接或文件>", commands)
        self.assertIn("详细拆解：<链接或文件>", commands)
        self.assertIn("逐字稿", commands["同步笔记：<链接或文件>"])
        self.assertIn("拉片", commands["蒸馏笔记：<链接或文件>"])
        self.assertIn("完整包含", commands["详细拆解：<链接或文件>"])

    def test_optional_route_cannot_be_selected_during_init(self) -> None:
        for agent in ("codex", "workbuddy"):
            with self.subTest(agent=agent):
                args = self.init_args(agent, "wechat")
                with self.assertRaisesRegex(ValueError, "Start with the desktop route"):
                    MODULE.command_init(args)

    def init_args(self, agent: str, channel: str, folder: str = "notes"):
        return type(
            "Args",
            (),
            {
                "agent": agent,
                "channel": channel,
                "notes_root": str(self.root / folder),
            },
        )()

    def fake_detection(self, agent: str) -> dict:
        return {
            "software": {"obsidian": "/Applications/Obsidian.app", agent: agent},
            "vault": {"registered_in_obsidian": False},
        }

    def test_desktop_route_still_requires_mobile_acceptance(self) -> None:
        args = self.init_args("codex", "desktop")
        with mock.patch.object(
            MODULE, "detected", return_value=self.fake_detection("codex")
        ):
            MODULE.command_init(args)
        state = MODULE.read_json(MODULE.state_path())
        self.assertEqual(state["steps"]["channel_connected"]["status"], "complete")
        self.assertEqual(state["steps"]["channel_test"]["status"], "complete")
        self.assertEqual(state["steps"]["desktop_test"]["status"], "pending")
        self.assertEqual(state["steps"]["mobile_connected"]["status"], "pending")
        self.assertEqual(state["steps"]["mobile_test"]["status"], "pending")

    def test_wechat_route_requires_connection_and_channel_test(self) -> None:
        args = self.init_args("workbuddy", "desktop")
        with mock.patch.object(
            MODULE, "detected", return_value=self.fake_detection("workbuddy")
        ):
            MODULE.command_init(args)
        self.complete_core_steps()
        MODULE.command_set_channel(type("Args", (), {"channel": "wechat"})())
        state = MODULE.read_json(MODULE.state_path())
        self.assertEqual(state["steps"]["channel_connected"]["status"], "pending")
        self.assertEqual(state["steps"]["channel_test"]["status"], "pending")
        self.assertEqual(state["steps"]["mobile_connected"]["status"], "complete")
        self.assertEqual(state["steps"]["mobile_test"]["status"], "complete")

    def test_changing_route_resets_old_acceptance_evidence(self) -> None:
        desktop = self.init_args("workbuddy", "desktop")
        with mock.patch.object(
            MODULE, "detected", return_value=self.fake_detection("workbuddy")
        ):
            MODULE.command_init(desktop)
        self.complete_core_steps()
        MODULE.command_set_channel(type("Args", (), {"channel": "feishu"})())
        state = MODULE.read_json(MODULE.state_path())
        for step in ("channel_connected", "channel_test"):
            state["steps"][step] = {
                "status": "complete",
                "evidence": f"old:{step}",
                "updated_at": MODULE.now(),
            }
        MODULE.atomic_json(MODULE.state_path(), state)
        MODULE.command_set_channel(type("Args", (), {"channel": "wechat"})())
        state = MODULE.read_json(MODULE.state_path())
        self.assertEqual(state["steps"]["desktop_test"]["status"], "complete")
        self.assertEqual(state["steps"]["channel_connected"]["status"], "pending")
        self.assertEqual(state["steps"]["channel_test"]["status"], "pending")

    def complete_core_steps(self) -> None:
        state = MODULE.read_json(MODULE.state_path())
        for step in MODULE.CORE_STEPS:
            state["steps"][step] = {
                "status": "complete",
                "evidence": f"verified:{step}",
                "updated_at": MODULE.now(),
            }
        MODULE.atomic_json(MODULE.state_path(), MODULE.normalize_state(state))

    def test_optional_channel_cannot_be_selected_before_core_setup(self) -> None:
        args = self.init_args("workbuddy", "desktop")
        with mock.patch.object(
            MODULE, "detected", return_value=self.fake_detection("workbuddy")
        ):
            MODULE.command_init(args)
        selection = type("Args", (), {"channel": "wechat"})()
        with self.assertRaisesRegex(RuntimeError, "Finish core setup"):
            MODULE.command_set_channel(selection)

    def test_optional_channel_preserves_completed_core_steps(self) -> None:
        args = self.init_args("workbuddy", "desktop")
        with mock.patch.object(
            MODULE, "detected", return_value=self.fake_detection("workbuddy")
        ):
            MODULE.command_init(args)
        self.complete_core_steps()

        selection = type("Args", (), {"channel": "wechat"})()
        MODULE.command_set_channel(selection)
        state = MODULE.read_json(MODULE.state_path())

        self.assertEqual(state["channel"], "wechat")
        for step in MODULE.CORE_STEPS:
            self.assertEqual(state["steps"][step]["status"], "complete")
        self.assertEqual(state["steps"]["channel_connected"]["status"], "pending")
        self.assertEqual(state["steps"]["channel_test"]["status"], "pending")

    def test_codex_can_select_wechat_after_core_setup(self) -> None:
        args = self.init_args("codex", "desktop")
        with mock.patch.object(
            MODULE, "detected", return_value=self.fake_detection("codex")
        ):
            MODULE.command_init(args)
        self.complete_core_steps()

        selection = type("Args", (), {"channel": "wechat"})()
        MODULE.command_set_channel(selection)
        state = MODULE.read_json(MODULE.state_path())
        self.assertEqual(state["agent"], "codex")
        self.assertEqual(state["channel"], "wechat")
        self.assertEqual(state["steps"]["channel_connected"]["status"], "pending")
        self.assertEqual(state["steps"]["channel_test"]["status"], "pending")

    def test_feishu_docs_destination_requires_core_setup(self) -> None:
        args = self.init_args("codex", "desktop")
        with mock.patch.object(
            MODULE, "detected", return_value=self.fake_detection("codex")
        ):
            MODULE.command_init(args)
        selection = type(
            "Args",
            (),
            {"destination": "obsidian-feishu", "evidence": "test doc read back"},
        )()
        with self.assertRaisesRegex(RuntimeError, "Finish core setup"):
            MODULE.command_set_destination(selection)

    def test_feishu_docs_destination_requires_readback_evidence(self) -> None:
        args = self.init_args("codex", "desktop")
        with mock.patch.object(
            MODULE, "detected", return_value=self.fake_detection("codex")
        ):
            MODULE.command_init(args)
        self.complete_core_steps()
        selection = type(
            "Args", (), {"destination": "obsidian-feishu", "evidence": ""}
        )()
        with self.assertRaisesRegex(ValueError, "created and read-back"):
            MODULE.command_set_destination(selection)

    def test_feishu_docs_destination_is_persisted_after_readback(self) -> None:
        args = self.init_args("codex", "desktop")
        with mock.patch.object(
            MODULE, "detected", return_value=self.fake_detection("codex")
        ):
            MODULE.command_init(args)
        self.complete_core_steps()
        selection = type(
            "Args",
            (),
            {
                "destination": "obsidian-feishu",
                "evidence": "https://example.feishu.cn/docx/test",
            },
        )()
        MODULE.command_set_destination(selection)
        config = MODULE.read_json(MODULE.config_path())
        state = MODULE.read_json(MODULE.state_path())
        self.assertEqual(config["destination"], "obsidian-feishu")
        self.assertEqual(state["destination"], "obsidian-feishu")

    def test_workbuddy_cannot_claim_feishu_docs_destination(self) -> None:
        args = self.init_args("workbuddy", "desktop")
        with mock.patch.object(
            MODULE, "detected", return_value=self.fake_detection("workbuddy")
        ):
            MODULE.command_init(args)
        self.complete_core_steps()
        selection = type(
            "Args",
            (),
            {"destination": "obsidian-feishu", "evidence": "test doc read back"},
        )()
        with self.assertRaisesRegex(ValueError, "Codex only"):
            MODULE.command_set_destination(selection)


if __name__ == "__main__":
    unittest.main()
