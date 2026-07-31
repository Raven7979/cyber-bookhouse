# WorkBuddy onboarding

Use this route only when WorkBuddy is the selected desktop Agent.

## Sequence

1. Run `doctor`. Install only missing prerequisites from `software-links.md`.
2. Confirm this Skill is visible and enabled in WorkBuddy.
3. Ask whether the user wants `desktop`, `feishu`, or `wechat`.
4. Run `setup_state.py init --agent workbuddy --channel <choice>`.
5. Open the configured notes folder as an Obsidian vault.
6. Open `欢迎来到赛博三味书屋.md` in Obsidian and confirm visible text.
7. Mark `vault_registered` with the vault path as evidence.
8. In WorkBuddy, send `收进书屋：https://example.com`.
9. Open the resulting note in Obsidian and verify its source link and body.
10. Mark `desktop_test` with the note path.
11. If `desktop` was selected, run `status` and finish.
12. Otherwise open WorkBuddy → Assistant settings and choose the selected
    integration:
    - `wechat`: follow the official WeChat Assistant guide. Require WorkBuddy
      4.6.4 or newer and WeChat 8.0.70 or newer; binding is by QR code and does
      not require App ID or App Secret.
    - `feishu`: follow the official Feishu guide. A Feishu enterprise account
      with permission to create an app may be required.
13. Let the user complete login, QR scanning, and authorization in the official
    UI. Do not request credentials in chat.
14. Enable WorkBuddy startup at login and confirm the selected connection
    remains available after WorkBuddy restarts.
15. Mark `channel_connected` with a non-sensitive connection-status summary.
16. In the selected mobile channel, send `收进书屋：https://example.com`.
17. Verify a reply arrives and the new note is visible in the same Obsidian
    vault. Mark `channel_test` with the note path and reply summary.

Do not invent menu names if the installed WorkBuddy version differs from this
guide. Use the application's current UI or official help. Explain that remote
input is unavailable while the computer is off, asleep, offline, or WorkBuddy
is not running.
