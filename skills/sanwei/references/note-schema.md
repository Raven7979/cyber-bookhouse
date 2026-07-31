# Note schema

Create one portable Markdown note per source.

```yaml
---
title: Example title
source_url: https://example.com
source_platform: web
content_type: article
captured_at: 2026-07-31T14:00:00+08:00
capture_id: 20260731-a1b2c3d4
note_mode: standard
acquisition_method: public_page
content_status: full_text
media_status: not_requested
transcript_status: unavailable
status: captured
tags:
  - content/article
  - status/captured
---
```

Use this body:

```markdown
# Example title

> 来源：[打开原文](https://example.com)

## 一句话摘要

## 核心内容

## 关键事实与待验证

## 可复用结论
```

For audio or video, add timestamped transcript and proofreading sections only
when source subtitles or actual ASR evidence exists. Use relative paths for
local assets. Never create a related-note link unless the linked note was read.

Use these controlled values:

- `note_mode`: `standard`, `cangjie`, or `detailed`.
- `acquisition_method`: `public_page`, `authorized_browser`, `user_file`,
  `official_export`, or `rss`.
- `content_status`: `full_text`, `partial`, `metadata_only`, or `unavailable`.
- `media_status`: `local`, `remote_only`, `not_requested`, or `unavailable`.
- `transcript_status`: `official`, `asr_raw`, `asr_proofread`, `unavailable`,
  or `not_requested`.

If only metadata was accessible, keep the note useful with the title, creator,
platform, source link, duration or publish time when visible, and an explicit
access limitation. Do not populate summary sections as if the full source had
been read.
