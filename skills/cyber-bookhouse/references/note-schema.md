# 固定笔记格式

每个来源生成一篇可迁移 Markdown。栏目结构是固定接口，不是写作建议：模型只填写内容，不得自行改名、换序、合并或增加同级栏目。

## YAML 属性

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
visual_assets: []
destinations:
  - obsidian
tags:
  - content/article
  - status/captured
---
```

`destinations` 必须包含 `obsidian`。只有飞书文档已经创建并读回成功，才能追加 `feishu_doc` 和 `feishu_doc_url`；失败时不得保存未验证链接。

受控值：

- `note_mode`：`standard`、`distilled`、`detailed`。
- `acquisition_method`：`public_page`、`authorized_browser`、`user_file`、`official_export`、`rss`。
- `content_status`：`full_text`、`partial`、`metadata_only`、`unavailable`。
- `media_status`：`local`、`remote_only`、`not_requested`、`unavailable`。
- `transcript_status`：`official`、`asr_raw`、`asr_proofread`、`unavailable`、`not_requested`。

## 同步笔记唯一结构

文章、图文和文档必须且只能按以下二级栏目排序：

```markdown
# {{标题}}

## 来源

- 作者：{{作者或“未取得”}}
- 发布时间：{{时间或“未取得”}}
- 原链接：{{完整原链接}}
- 采集时间：{{采集时间}}

## 一句话摘要

{{一句能够独立理解的结论}}

## 核心内容

**{{要点一短标题。}}** {{来源内容、证据与必要边界}}

**{{要点二短标题。}}** {{来源内容、证据与必要边界}}

**{{要点三短标题。}}** {{来源内容、证据与必要边界}}

## 内容脉络

1. {{推进步骤一}}
2. {{推进步骤二}}
3. {{推进步骤三}}

## 关键事实与待验证

| 项目 | 来源中的说法或观察 | 本次状态 |
| --- | --- | --- |
| {{项目}} | {{原说法或可见事实}} | {{已确认／来源陈述／待独立核验}} |

## 自动标签

{{3–7 个有证据的语义标签，并包含来源和状态标签}}
```

当真实取得视频、音频、来源字幕或 ASR 时，再按固定顺序追加以下两个栏目：

```markdown
## 逐字稿与画面证据

**{{00:00–00:30}}** {{覆盖该时段的完整语义段，不写成摘要}}

{{紧跟对应时段的真实画面和图注}}

## 校对记录

- {{逐字稿来源与覆盖范围}}
- {{依据画面、字幕或元数据完成的校正}}
- {{仍未确认的词、数字或事实；没有则写“无”}}
```

只有元数据、没有真实媒体或逐字稿时，不得添加这两个栏目冒充内容；在正文中准确写明访问限制。

## 蒸馏笔记唯一结构

`note_mode: distilled` 不使用标准摘要栏目。文章必须且只能使用：`来源` → `蒸馏笔记`。有真实媒体证据的视频或音频必须且只能使用：`来源` → `逐字稿与画面证据` → `校对记录` → `蒸馏笔记`。

“蒸馏笔记”内部可用三级标题组织内容骨架与批判、核心方法、行动清单、案例与反例、术语、关系和压力测试，但不得增加其他二级栏目。

## 详细拆解唯一结构

`note_mode: detailed` 完整保留“同步笔记”的固定栏目，并且只在末尾增加一个 `## 蒸馏笔记`。不得把蒸馏内容拆成多个二级栏目。

## 不可变规则

- 正文只允许当前模式规定的二级栏目；不得新增“原文文案”“视频时间线”“画面观察”“关键画面”“金句总结”“可复用结论”等平级栏目。
- 可核对原话、结构图和额外分析放进最相近的固定栏目；需要层次时使用加粗短语、列表、表格或三级标题。
- 原链接必须出现在“来源”栏目内。
- 视频画面紧跟它所证明的时间码段，不集中堆成文末图库。
- 没有真实证据时写明 `metadata_only`、`partial` 或 `unavailable`，不得补写摘要、逐字稿、镜头或事实。
- 结构图的相对 SVG 路径写入 `visual_assets`，文件存在并成功打开后再嵌入相应正文位置。

写完后必须运行：

```bash
<python-command> "<skill-dir>/scripts/validate_note.py" "<note-path>"
```

返回 `ready: false` 时修正同一文件并重跑；不得把模型自检当作格式验收。
