# 普通网页采集

先用包内脚本读取公开 HTML 中真实可见的文字：

```bash
<python-command> "<skill-dir>/scripts/web_capture.py" "URL" \
  --output-dir "<vault>/链接采集/_assets/<capture-id>"
```

它不使用浏览器 Cookie，不访问本机或局域网地址，不绕过登录、付费墙或验证码。
一条页面动态渲染、需要登录或脚本只读到导航时，不要将结果写成全文。

如果当前 Codex / WorkBuddy 能操作用户明确授权的可见浏览器页面：

1. 只读取屏幕上已显示的正文；
2. 把可见文字导出为 UTF-8 文本；
3. 使用 `--staged-text` 写入回执；
4. 不导出 Cookie、Local Storage、请求头或账号凭据。

```bash
<python-command> "<skill-dir>/scripts/web_capture.py" "URL" \
  --staged-text "/path/to/visible-page.txt" \
  --title "页面标题" \
  --output-dir "<vault>/链接采集/_assets/<capture-id>"
```

`receipt.json` 中的 `content_status` 才是能否总结全文的依据。
`metadata_only` 不得用于完整总结。
