# Codex onboarding

Use this route only when Codex is the selected desktop Agent.

## Sequence

1. Run `doctor`. For desktop-only use, either the ChatGPT desktop app with
   Codex mode or Codex CLI is sufficient. The Feishu bridge specifically
   requires Codex CLI installed and logged in.
2. Ask whether the user wants `desktop` or `feishu`. Do not offer WeChat on
   this route.
3. Run `setup_state.py init --agent codex --channel <choice>`.
4. Open the configured notes folder as an Obsidian vault.
5. Open `欢迎来到赛博三味书屋.md` in Obsidian and confirm visible text.
6. Mark `vault_registered` with the vault path as evidence.
7. Send a local test request to Codex: `收进书屋：https://example.com`.
8. Open the resulting note in Obsidian and verify its source link and body.
9. Mark `desktop_test` with the note path.
10. If `desktop` was selected, run `status` and finish. If `feishu` was
    selected, configure it:
   - Ensure Codex CLI is installed and logged in.
   - Ensure Node.js 20.12.0 or newer is installed.
   - Install the bridge from its official package:
     `npm install -g lark-channel-bridge`.
   - Run `lark-channel-bridge run --agent codex`.
   - Let the user scan the displayed QR code and finish Feishu authorization.
   - Do not ask the user to paste an App Secret into chat.
   - After the foreground test works, stop it and run
     `lark-channel-bridge start --agent codex`.
   - Confirm `lark-channel-bridge status` reports a healthy background service.
11. Mark `channel_connected` with the bridge status, not with a secret or ID.
12. In Feishu, send `收进书屋：https://example.com`.
13. Verify a reply arrives and the new note is visible in the same Obsidian
    vault. Mark `channel_test` with the note path and a non-sensitive reply
    summary.

Do not mark setup complete if the computer must still keep a foreground
terminal open. The background bridge must recover after login. Explain that
Feishu input is unavailable while the computer is off, asleep, or offline.
