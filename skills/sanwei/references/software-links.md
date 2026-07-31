# Official software sources

Use these sources. Do not bundle third-party installers in the project.

| Software | Official source | Required for |
| --- | --- | --- |
| Obsidian | https://obsidian.md/download | Every route |
| ChatGPT desktop with Codex | https://chatgpt.com/download/ | Codex desktop route |
| Codex CLI | https://developers.openai.com/codex/cli | Codex-to-Feishu route |
| WorkBuddy | https://www.codebuddy.cn/work/ | WorkBuddy route |
| WorkBuddy Skill help | https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market | Installing this Skill in WorkBuddy |
| WorkBuddy Assistant help | https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Assistant | WorkBuddy remote inputs |
| WorkBuddy WeChat guide | https://www.codebuddy.cn/docs/workbuddy/WeixinBot-Guide | WorkBuddy-to-WeChat route |
| WorkBuddy Feishu guide | https://www.codebuddy.cn/docs/workbuddy/Feishu-Guide | WorkBuddy-to-Feishu route |
| Feishu | https://www.feishu.cn/download | Feishu input |
| Node.js 20.12.0+ | https://nodejs.org/en/download | Codex-to-Feishu bridge |
| Lark Channel Bridge | https://github.com/zarazhangrui/lark-coding-agent-bridge | Codex-to-Feishu bridge |
| Lark / Feishu CLI | https://github.com/larksuite/cli | Optional Codex-to-Feishu-Docs output |
| yt-dlp | https://github.com/yt-dlp/yt-dlp#installation | YouTube public metadata and subtitles |
| FFmpeg | https://ffmpeg.org/download.html | Local audio/video processing and validation |
| Whisper | https://github.com/openai/whisper | Optional local speech transcription |
| MLX Whisper | https://github.com/ml-explore/mlx-examples/tree/main/whisper | Optional local speech transcription on Apple silicon |

When a required application is missing:

1. Show only the relevant official link.
2. Explain why it is needed in one sentence.
3. Wait for installation to finish.
4. Run `doctor` again before proceeding.

If the user explicitly asks the desktop Agent to install software, download it
from the official source and verify the installed application or executable.
Never fetch an installer from a reposting site.
