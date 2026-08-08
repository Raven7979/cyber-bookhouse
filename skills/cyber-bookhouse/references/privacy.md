# Privacy and connector policy

## Defaults

- Keep notes, local files, screenshots, and media on the user's computer.
- Collect the minimum evidence needed for the requested note.
- Preserve source attribution and acquisition limitations.
- Do not read or copy browser cookies, profiles, tokens, passwords, App Secrets,
  webhooks, private Skills, Agent memory, or unrelated vault content.
- Do not place credentials in Markdown, setup evidence, logs, examples, or Git.
- Use official APIs, exports, and user-provided files before browser automation.
- Do not bypass authentication, CAPTCHA, paywalls, DRM, rate limits, or platform
  access controls.
- The bundled X route may obtain X's current public web-client configuration and
  a short-lived anonymous guest token from official X endpoints. Keep these
  values in memory only; never print, persist, return, or reuse them as user
  credentials. It never reads the user's X account, cookies, or browser state.

## New connectors

Before adding a platform connector, document:

1. Official interface or user-controlled export used.
2. Data sent off-device, recipient, purpose, and retention.
3. Required scopes and why each is necessary.
4. Failure behavior when content is unavailable.
5. Deletion and revocation procedure.

An inaccessible page is a failed acquisition, not permission to guess or bypass.
