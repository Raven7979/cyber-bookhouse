# 第一次安装

第一次只需要你亲手做一件事：把 `sanwei` Skill 交给 Codex 或
WorkBuddy。它认得这套 Skill 以后，后面的软件检查、Obsidian 设置、手机
连接和测试都会一项一项带你完成。

不知道选哪个也没关系：

- 平时用 ChatGPT，选 Codex。
- 平时用 WorkBuddy，选 WorkBuddy。
- 两个都没用过，先选一个，不必同时安装。

## 先看系统

| 系统 | 状态 | 安装时会有什么不同 |
| --- | --- | --- |
| macOS | 稳定 | 默认书屋在 `~/Documents/cyber-sanwei` |
| Windows 10 / 11 | Beta | 默认书屋在 `%USERPROFILE%\Documents\cyber-sanwei`，脚本使用 PowerShell 和 `py -3` |
| Linux | 本版未支持 | 暂不提供自动安装向导 |

Windows 版会检查 `%LOCALAPPDATA%`、`%APPDATA%` 和常见应用目录。
因为目前是 Beta，只有电脑、手机和 Obsidian 的真实写入测试都通过，
向导才会告诉你“安装完成”。

## 用 WorkBuddy 安装

1. 安装并打开 [WorkBuddy](https://www.codebuddy.cn/work/)。
2. 打开「技能」，点击「添加技能」→「上传技能」。
3. 选择发布页下载的 `sanwei.zip`。
4. 确认「赛博三味书屋」已经出现在已安装技能中。
5. 新建一个任务，发送：

> 请使用 sanwei Skill，一步一步帮我搭好赛博三味书屋。每次只告诉我
> 一个操作，做完再继续。最后请从手机发一个测试链接，并确认笔记进入
> Obsidian。基础测试通过后，再问我要不要增加飞书入口或微信。最后运行
> 包内能力检查，告诉我哪些内容可以直接处理。

WorkBuddy 的官方说明：

- [Windows 10+ 安装指南](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Installation-Win-Guide)
- [安装 Skill](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)
- [在手机上远程使用 WorkBuddy](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Practice-Cases/Practice-Six)

## 用 Codex 安装

1. 安装并打开
   [Codex 桌面应用](https://openai.com/index/introducing-the-codex-app/)；已经在用
   Codex CLI 的人也可以继续使用。
2. 解压发布页下载的 `sanwei.zip`。
3. 把解压后的 `sanwei` 文件夹拖进 Codex 对话，并发送：

> 请把这个 sanwei 文件夹安装为我的用户级 Skill。macOS 安装到
> ~/.agents/skills/sanwei，Windows 安装到
> %USERPROFILE%\.agents\skills\sanwei。回读 SKILL.md 并确认 /skills 中能看到
> sanwei；不要改动我已有的其他 Skills。

4. 安装确认后发送：

> 请使用 $sanwei，一步一步帮我搭好赛博三味书屋。每次只告诉我一个
> 操作，做完再继续。最后请从 ChatGPT 手机端发一个测试链接，并确认
> 笔记进入 Obsidian。基础测试通过后，再问我要不要增加飞书入口或飞书
> 文档。最后运行包内能力检查，告诉我哪些内容可以直接处理。

如果 Skill 没有马上出现，重启 Codex 后再看一次。

Codex 在 ChatGPT 手机端中逐步开放。更新桌面端和手机端后，可以从手机
进入电脑上的 Codex 任务，继续发消息、查看结果和确认操作。官方说明：
[在手机上使用 Codex](https://openai.com/index/work-with-codex-from-anywhere/)。

Windows 上如果 `py -3` 和 `python` 都不可用，向导会只给你
[Python 官方 Windows 下载](https://www.python.org/downloads/windows/)，等你安装完再继续。

## 接下来会发生什么

向导会依次做这几件事：

1. 找到或新建一个 Obsidian 书屋。新建时使用上表对应的英文磁盘目录，
   中文“赛博三味书屋”用于欢迎页和提示。
2. 识别当前运行 Skill 的桌面 Agent 是 Codex 还是 WorkBuddy。
3. 帮你接好 ChatGPT 或 WorkBuddy 手机端。
4. 从电脑和手机各发一次测试链接。
5. 基础测试完成后，再问你只用当前工具，还是增加飞书入口或微信；Codex
   用户还可以选择飞书文档输出。
6. 在 Obsidian 里打开结果给你看。
7. 如果选择飞书文档，再创建并读回一份测试文档；只创建成功不算接通。
8. 运行包内能力检查，区分可直接处理、需要浏览器和需要用户文件的内容。
9. 告诉你“同步笔记、蒸馏笔记、详细拆解”三种日常命令。

新建目录后，向导会先通过 Obsidian 的“打开文件夹作为仓库”完成注册，
再打开欢迎笔记。注册前不会直接调用 `obsidian://open?path=...`，否则
Obsidian 会提示 `Vault not found`。

它不会让你把密码、Token、App Secret、Cookie 或私人文档贴进对话。
需要登录、扫码或授权时，它只会把你带到对应软件自己的界面。
