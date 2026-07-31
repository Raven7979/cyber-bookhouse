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
        MODULE.atomic_json(target, {"name": "赛博三味书屋"})
        self.assertEqual(MODULE.read_json(target)["name"], "赛博三味书屋")

    def test_default_new_vault_uses_ascii_directory_name(self) -> None:
        self.assertEqual(MODULE.DEFAULT_VAULT_DIRNAME, "cyber-sanwei")
        self.assertTrue(MODULE.DEFAULT_VAULT_DIRNAME.isascii())
        self.assertEqual(MODULE.VAULT_DISPLAY_NAME, "赛博三味书屋")

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
        self.assertEqual(config["vault_display_name"], "赛博三味书屋")
        self.assertTrue((default_notes / "欢迎来到赛博三味书屋.md").is_file())

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

    def test_codex_rejects_wechat_route(self) -> None:
        args = type(
            "Args",
            (),
            {
                "agent": "codex",
                "channel": "wechat",
                "notes_root": str(self.root / "notes"),
            },
        )()
        with self.assertRaisesRegex(ValueError, "only through WorkBuddy"):
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
        args = self.init_args("workbuddy", "wechat")
        with mock.patch.object(
            MODULE, "detected", return_value=self.fake_detection("workbuddy")
        ):
            MODULE.command_init(args)
        state = MODULE.read_json(MODULE.state_path())
        self.assertEqual(state["steps"]["channel_connected"]["status"], "pending")
        self.assertEqual(state["steps"]["channel_test"]["status"], "pending")
        self.assertEqual(state["steps"]["mobile_connected"]["status"], "pending")
        self.assertEqual(state["steps"]["mobile_test"]["status"], "pending")

    def test_changing_route_resets_old_acceptance_evidence(self) -> None:
        desktop = self.init_args("workbuddy", "desktop")
        remote = self.init_args("workbuddy", "wechat")
        with mock.patch.object(
            MODULE, "detected", return_value=self.fake_detection("workbuddy")
        ):
            MODULE.command_init(desktop)
            state = MODULE.read_json(MODULE.state_path())
            state["steps"]["desktop_test"] = {
                "status": "complete",
                "evidence": "old-note.md",
                "updated_at": MODULE.now(),
            }
            MODULE.atomic_json(MODULE.state_path(), state)
            MODULE.command_init(remote)
        state = MODULE.read_json(MODULE.state_path())
        self.assertEqual(state["steps"]["desktop_test"]["status"], "pending")
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

    def test_codex_wechat_is_rejected_after_core_setup(self) -> None:
        args = self.init_args("codex", "desktop")
        with mock.patch.object(
            MODULE, "detected", return_value=self.fake_detection("codex")
        ):
            MODULE.command_init(args)
        self.complete_core_steps()

        selection = type("Args", (), {"channel": "wechat"})()
        with self.assertRaisesRegex(ValueError, "only through WorkBuddy"):
            MODULE.command_set_channel(selection)


if __name__ == "__main__":
    unittest.main()
