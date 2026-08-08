# X 公开帖子与 X Article

只对公开的 `x.com/.../status/<id>` 或 `twitter.com/.../status/<id>` 使用包内路线：

```bash
<python-command> "<skill-dir>/scripts/x_capture.py" "URL" \
  --output-dir "<vault>/链接采集/_assets/<capture-id>"
```

脚本不读取 X 账号、浏览器 Cookie 或本机浏览器状态。普通公开帖子通过 X 的公开
嵌入数据保存真实配文、作者、发布时间和媒体元数据。帖子引用 X Article 时，脚本
再从 X 官方公开网页取得当前 Web 客户端配置，申请短时匿名 guest token，并向 X
官方接口请求完整正文。这些临时值只在内存中使用，不写入文件、日志或回执。

## 完整性门禁

X Article 只有同时满足以下条件才写成完整正文：

1. 原 status ID 与公开帖子数据一致；
2. 帖子中的 Article ID、Article URL 和完整正文返回的 `rest_id` 一致；
3. DraftJS 富文本或 `plain_text` 包含真实正文，而不只是预览、短链或登录提示；
4. 正文成功转换为 Markdown。

任一条件失败时，脚本以 `X_ARTICLE_BODY_UNAVAILABLE` 退出，不创建伪完整
`content.md`。不要改用普通网页脚本把登录页、预览文字或短链当作正文。

## 图片与视频边界

- X Article 原图只从 `https://pbs.twimg.com` 下载，并要求跳转后仍是同域 HTTPS。
- 最多 30 张；单张上限 80 MiB，总上限 400 MiB，总下载时间上限 300 秒。
- 只接受经过文件头确认的 JPEG、PNG、GIF 或 WebP。HTML、SVG 和未知类型会被拒绝。
- 图片部分失败时保留已验证的完整正文；`receipt.json` 会写明
  `images_incomplete` 和唯一原因，不能据此把正文降成预览。
- 普通 X 视频帖子可以保存公开配文和媒体元数据，但没有取得本地视频与真实转写时，
  `receipt.json` 必须保持 `partial`，不能声称视频本体已经完整处理。

## 输出与降级

成功后读取同目录的 `receipt.json`：

- `content.md`：普通帖子正文或 X Article 完整 Markdown；
- `assets/`：已验证并下载的 Article 图片；
- `content_status`：`full_text`、`partial` 或 `metadata_only`；
- `status`：只有证据满足完整性门禁时才是 `complete`。

删除、私密、地区限制、年龄限制、频率限制或 X 上游接口变化都可能使公开路线失败。
此时保留原链接和错误边界，必要时让用户提供官方导出或自己有权使用的本地文件；
不要反复重试、绕过限制或索要 X Cookie。
