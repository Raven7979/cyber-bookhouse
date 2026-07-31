# Windows 安装与验收

Windows 路线使用 PowerShell，支持等级为 `beta`。这表示包内的路径、
应用检测、依赖检查和笔记脚本已支持 Windows，但必须在用户当前
电脑上完成真实验收，才能说“已安装完成”。

## 开始前

1. 确认系统是 Windows 10 或 Windows 11。
2. 使用当前已打开的 Codex 或 WorkBuddy，不要在安装开始时询问
   飞书或微信助理。
3. 在 PowerShell 中确定 Python 命令：

```powershell
py -3 --version
```

如果 `py -3` 不可用，再试 `python --version`。两个都不可用时，
从 [software-links.md](software-links.md) 中的 Python 官方地址安装，完成后
重新检查。

## 默认路径

- 书屋目录：`%USERPROFILE%\Documents\cyber-sanwei`
- 配置：`%LOCALAPPDATA%\cyber-sanwei\config.json`
- 安装状态：`%LOCALAPPDATA%\cyber-sanwei\data\setup.json`
- Obsidian 仓库登记：`%APPDATA%\obsidian\obsidian.json`

新建目录继续使用英文 `cyber-sanwei`，中文名“赛博三味书屋”用在
欢迎页和对用户的提示中。

## 核心安装

把 `<skill-dir>` 替换为当前 `sanwei` Skill 的绝对路径：

```powershell
py -3 "<skill-dir>\scripts\setup_state.py" doctor
py -3 "<skill-dir>\scripts\setup_state.py" init --agent codex --channel desktop
```

WorkBuddy 路线把 `codex` 换成 `workbuddy`。如果本机只能使用 `python`，
就把命令开头的 `py -3` 换成 `python`。

初始化后：

1. 在 Obsidian 中选择“打开文件夹作为仓库”。
2. 选择 `%USERPROFILE%\Documents\cyber-sanwei`。
3. 重新运行 `doctor`，确认 `registered_in_obsidian` 为 `true`。
4. 在 Obsidian 中打开中文欢迎笔记做可见性验收。

不要用 `obsidian://open?path=...` 注册新仓库。

## 依赖检查

```powershell
py -3 "<skill-dir>\scripts\dependency_doctor.py"
```

- 本地音视频需要 FFmpeg。
- YouTube 公开元数据和字幕需要 `yt-dlp`。
- Windows 本地语音转写使用 OpenAI Whisper，不安装只适用于
  Apple silicon 的 MLX Whisper。
- 缺少的软件只从 [software-links.md](software-links.md) 中的官方地址安装，
  不把安装程序塞进 Skill 包。

## 非默认安装位置

检查脚本会查找常见的 Windows 安装目录。如果用户把应用放在其他
磁盘，只在当前 PowerShell 会话设置对应路径，不改动系统配置：

```powershell
$env:CYBER_SANWEI_OBSIDIAN_APP = "D:\Apps\Obsidian\Obsidian.exe"
$env:CYBER_SANWEI_WORKBUDDY_APP = "D:\Apps\WorkBuddy\WorkBuddy.exe"
$env:CYBER_SANWEI_CHATGPT_APP = "D:\Apps\ChatGPT\ChatGPT.exe"
$env:CYBER_SANWEI_CODEX_APP = "D:\Apps\Codex\Codex.exe"
```

只设置实际需要的项，然后重新运行 `doctor`。

## Windows 真实验收

Windows 上的安装不能用“文件已创建”代替真实测试，必须完成：

1. `doctor` 识别到当前桌面 Agent 和 Obsidian。
2. 电脑端发送一条测试链接，笔记在 Obsidian 中可见。
3. ChatGPT 或 WorkBuddy 手机端发送一条测试链接，写入同一书屋并
   收到回复。
4. 核心测试通过后，再询问是否增加飞书或微信助理；Codex 用户选择微信
   时也按 [wechat-assistant.md](wechat-assistant.md) 引导安装或打开 WorkBuddy。
5. 如果选了额外入口，从该入口再做一次同书屋写入和回复测试。
6. 运行 `status`，只有全部必要步骤都有验收证据时，才告诉用户
   安装完成并发送三种日常命令。

电脑关机、深度睡眠或断网时，手机、飞书和微信助理入口不能继续调用
这台电脑上的 Agent。
