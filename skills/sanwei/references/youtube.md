# YouTube 采集路线

这条路线只读取公开信息或用户明确授权后在浏览器中可见的字幕。它不自动
导出浏览器 Cookie，不绕过真人验证，也不把初始 HTML 当作完整页面。

## 第一步：检查依赖

```bash
<python-command> "<skill-dir>/scripts/dependency_doctor.py" --require youtube
```

缺少 `yt-dlp` 时，给出 [software-links.md](software-links.md) 中的官方链接，
等用户安装完成后再检查一次。

## 第二步：公开采集

为本次任务创建临时目录，然后运行包内脚本：

```bash
<python-command> "<skill-dir>/scripts/youtube_capture.py" "YOUTUBE_URL" \
  --output-dir "<temporary-dir>/sanwei-youtube-VIDEO_ID"
```

根据 `receipt.json` 处理：

- `complete`：使用真实字幕生成逐字稿。
- `partial`：只使用已经取得的元数据；需要逐字稿时继续下一步。
- `dependency_missing`：只提示安装缺少的软件。
- `authorization_required`：停止公开重试，继续下一步。
- `unavailable`：保留来源和具体错误，不写视频内容总结。

`dependency_doctor` 显示 YouTube 工具可用，只代表软件存在，不代表每条视频
都能访问。真实结果以这条 URL 的 `receipt.json` 为准。

## 第三步：可见浏览器降级

遇到 `authorization_required` 时，只问一次：

> YouTube 要求真人验证。你愿意让我打开这条视频的已登录页面，只读取页面
> 上可见的字幕文字吗？不会导出或保存浏览器 Cookie。

用户同意后：

1. 用当前 Agent 的浏览器能力打开原视频。
2. 等页面渲染完成，点击页面上的“显示字幕文字记录”或同义入口。
3. 只提取字幕面板中可见的文字和时间点，保存到临时文本文件。
4. 不读取浏览器配置目录，不运行 `--cookies-from-browser`，不导出 Cookie。
5. 把可见字幕交给包内脚本验收：

```bash
<python-command> "<skill-dir>/scripts/youtube_capture.py" "YOUTUBE_URL" \
  --output-dir "<temporary-dir>/sanwei-youtube-VIDEO_ID" \
  --staged-transcript "<temporary-dir>/visible-youtube-transcript.txt"
```

macOS 可把 `<temporary-dir>` 设为 `/tmp`；Windows PowerShell 使用 `$env:TEMP`。

如果当前 Agent 没有浏览器能力、页面没有字幕入口或用户不同意授权，就让
用户选择复制字幕文字，或提供字幕/视频文件。不要继续解析初始页面源码；
那里面通常没有动态加载后的字幕轨道。

## 时间点链接

链接含 `t=` 或 `start=` 时，只有在真实字幕或本地转写存在后，才能回答该
时间点附近的内容。否则在笔记中写明“指定时间点未取得”，不能用简介猜。

## 验收

- `metadata.json` 保留标题、作者和原链接；
- `receipt.json` 写明获取方式、状态、错误和下一条可行路线；
- 有真实字幕时才生成 `transcript.txt`；
- 最终笔记的 `transcript_status` 与回执一致；
- 同一个失败链接不在一次任务中重复尝试相同公开路线。
