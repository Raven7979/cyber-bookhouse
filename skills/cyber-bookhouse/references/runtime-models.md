# 模型、图片与视频能力检查

赛博书屋不会把“能读文件”“能看图片”和“能直接接收视频”混为一谈。
第一次处理图片或视频前，先运行能力检查，再用一张真实图片做宿主验收。

## Codex 当前建议

Codex 当前推荐 GPT-5.6 Sol、Terra 和 Luna。默认优先 Sol；日常处理可用
Terra；规则清楚的批量提取可用 Luna。三者都必须在当前 Codex 入口中通过
一张真实 PNG 或 JPEG 的读取测试，不能只凭模型名称判断。

视频不要求模型原生接收 MP4。赛博书屋采用下面的本地路线：

```text
本地视频 → FFmpeg 抽取代表帧 → 支持图片输入的模型识别画面
         → Whisper 本地转写 → 合并为 Markdown 笔记
```

因此硬性条件是：

1. 当前宿主能读取本地文件并运行工具；
2. 当前模型/入口能读取 PNG 或 JPEG；
3. 需要逐字稿时，本机 FFmpeg 和 Whisper 可用。

如果图片测试失败，只能生成逐字稿版，并明确标记“未完成画面核验”。
如果只取得代表帧但没有音频或字幕，不得猜测对白。

结构图也必须经过图片检查。文本模型可以生成 Mermaid，但当
`visual-report.json` 判定必须画图时，当前入口还必须能查看渲染后的 PNG；否则
只能报告 `visual_review_unavailable`，不能把“代码生成成功”写成“图已完成”。

## 其他宿主

Claude Code 和 WorkBuddy 的可选模型、入口和权限会变化。不要写死一个模型名，
而是在当前电脑上执行同样的真实图片测试。模型能描述文本但看不到图片时，
不宣称具备视频理解能力。

## Codex Browser 边界

Codex Browser 只在 ChatGPT 桌面应用和网页入口提供；Codex CLI 和 IDE 扩展
没有内置 Browser。需要浏览器自动化时，在桌面应用的 Plugins Directory
安装 Browser，并由用户在 **Settings → Browser → Developer mode** 中决定
是否启用完整 CDP 权限。

完整 CDP 可以暴露浏览器内部信息。只在明确网站和任务范围内申请，先说明风险，
由用户确认；不要读取、导出或打印 Cookie、Local Storage、密码、验证码或 Token。
Browser 是否可用还可能受套餐、工作区管理员策略和分批开放影响。

当前官方说明：

- https://learn.chatgpt.com/docs/models
- https://learn.chatgpt.com/docs/image-inputs
- https://learn.chatgpt.com/docs/browser
