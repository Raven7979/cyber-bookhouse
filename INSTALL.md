# 第一次安装

第一次只需要你亲手做一件事：把 `cyber-bookhouse` Skill 交给 Codex、Claude 或
WorkBuddy。它认得这套 Skill 以后，后面的软件检查、Obsidian 设置、入口
连接和测试都会一项一项带你完成。

不知道选哪个也没关系：

- 平时用 ChatGPT，选 Codex。
- 平时用 Claude，选 Claude Code。
- 平时用 WorkBuddy，选 WorkBuddy。
- 这些都没用过，先选一个，不必同时安装。

## 先看系统

| 系统 | 状态 | 安装时会有什么不同 |
| --- | --- | --- |
| macOS | 稳定 | 默认书屋在 `~/Documents/cyber-bookhouse` |
| Windows 10 / 11 | Beta | 默认书屋在 `%USERPROFILE%\Documents\cyber-bookhouse`，脚本使用 PowerShell 和 `py -3` |
| Linux | 本版未支持 | 暂不提供自动安装向导 |

Windows 版会检查 `%LOCALAPPDATA%`、`%APPDATA%` 和常见应用目录。
因为目前是 Beta，只有当前路线要求的入口和 Obsidian 真实写入测试都通过，
向导才会告诉你“安装完成”。

## 已安装用户更新

已经装进 Codex、Claude Code 或 WorkBuddy 的 Skill 不会自动更新。GitHub 发布新版后，
需要重新下载最新的 `cyber-bookhouse.zip` 并再次安装。

Codex 或 Claude Code 用户解压新版后，重新运行原安装命令：

```bash
python3 cyber-bookhouse/scripts/install_skill.py --target codex
# Claude Code：--target claude
# 两边都更新：--target both
```

安装器发现同名旧版时，会先将它移动到 `~/.cyber-bookhouse-backups/`，再安装新版并
逐文件回读校验；不会碰其他 Skills。更新后重启或新开一个 Agent 任务，再调用一次
`cyber-bookhouse`。WorkBuddy 用户重新上传最新版 ZIP，并在界面中确认更新或覆盖。

## 用 WorkBuddy 安装

1. 安装并打开 [WorkBuddy](https://www.codebuddy.cn/work/)。
2. 打开「技能」，点击「添加技能」→「上传技能」。
3. 选择发布页下载的 `cyber-bookhouse.zip`。
4. 确认「赛博书屋」已经出现在已安装技能中。
5. 新建一个任务，发送：

> 请使用 cyber-bookhouse Skill，一步一步帮我搭好赛博书屋。每次只告诉我
> 一个操作，做完再继续。最后请从手机发一个测试链接，并确认笔记进入
> Obsidian。基础测试通过后，再问我要不要增加飞书入口或微信助理。最后运行
> 包内能力检查，告诉我哪些内容可以直接处理。

WorkBuddy 的官方说明：

- [Windows 10+ 安装指南](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Installation-Win-Guide)
- [安装 Skill](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)
- [在手机上远程使用 WorkBuddy](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Practice-Cases/Practice-Six)
- [绑定微信助理](https://www.codebuddy.cn/docs/workbuddy/WeixinBot-Guide)

## 用 Codex 安装

1. 安装并打开
   [Codex 桌面应用](https://openai.com/index/introducing-the-codex-app/)；已经在用
   Codex CLI 的人也可以继续使用。
2. 把发布页下载的 `cyber-bookhouse.zip` 拖进 Codex 对话，并发送：

> 请解压这个 cyber-bookhouse.zip，运行包内 scripts/install_skill.py --target codex，
> 把它安装成我的用户级 Skill。安装器如遇同名旧版，先做可恢复备份；完成后
> 回读 SKILL.md，并确认 /skills 中能看到 cyber-bookhouse。不要改动其他 Skills。

3. 安装确认后发送：

> 请使用 $cyber-bookhouse，一步一步帮我搭好赛博书屋。每次只告诉我一个
> 操作，做完再继续。最后请从 ChatGPT 手机端发一个测试链接，并确认
> 笔记进入 Obsidian。基础测试通过后，再问我要不要增加飞书入口、微信
> 助理或飞书文档。如果我选择微信助理，请继续引导安装或打开 WorkBuddy，
> 上传同一份 Skill，绑定到同一个书屋并做真实回测。最后运行包内能力检查，
> 告诉我哪些内容可以直接处理。

如果 Skill 没有马上出现，重启 Codex 后再看一次。

Codex 在 ChatGPT 手机端中逐步开放。更新桌面端和手机端后，可以从手机
进入电脑上的 Codex 任务，继续发消息、查看结果和确认操作。官方说明：
[在手机上使用 Codex](https://openai.com/index/work-with-codex-from-anywhere/)。

Windows 上如果 `py -3` 和 `python` 都不可用，向导会只给你
[Python 官方 Windows 下载](https://www.python.org/downloads/windows/)，等你安装完再继续。

## 用 Claude Code 安装

1. 按 [Claude Code 官方文档](https://code.claude.com/docs/en/overview) 安装并
   登录 Claude Code。
2. 把发布页下载的 `cyber-bookhouse.zip` 放进当前任务可读的目录，解压后对 Claude 说：

> 请运行 cyber-bookhouse/scripts/install_skill.py --target claude，把它安装成我的用户级
> Skill。安装器如遇同名旧版，先做可恢复备份；完成后回读 SKILL.md，并确认
> /cyber-bookhouse 可以调用。不要改动其他 Skills。

3. 安装确认后发送：

> 请使用 /cyber-bookhouse，一步一步帮我搭好赛博书屋。每次只告诉我一个操作，做完
> 再继续。先完成 Claude 电脑端到 Obsidian 的真实写入测试，再问我要不要
> 增加飞书入口、微信助理或飞书文档。若选择微信助理，请继续引导安装或打开
> WorkBuddy，上传同一份 Skill，并写入同一个书屋。最后运行包内能力检查，
> 告诉我哪些内容可以直接处理。

Claude 的基础路线不声称已经接通手机。需要手机入口时，飞书由
`lark-channel-bridge` 连接本机 Claude Code；微信由 WorkBuddy 微信助理接收，
两者都必须用真实链接回测到同一个 Obsidian 书屋。

## 把飞书 Bot 接进赛博书屋

这一步只在基础 Obsidian 路线已经真实写入成功后进行。Skill 会先问你用新 Bot，还是
复用已有 Bot；不会要求你把 App Secret、Token 或 Cookie 发进对话。

### 没有 Bot：扫码创建

1. 向导检查 Node.js 20.12+，并安装 `lark-channel-bridge`。
2. 向导用当前 Agent 和已验收的书屋目录运行：

```bash
lark-channel-bridge run \
  --profile cyber-bookhouse \
  --agent codex \
  --workspace "<你的书屋目录>"
```

3. 终端出现二维码后，用飞书扫码，在官方页面选择或创建 PersonalAgent 应用。
4. 看到“已连接”后，在飞书里找到新 Bot，私聊发送 `/status`。
5. 再发一条真实的 `同步笔记：链接`，确认同一个 Obsidian 书屋出现可读笔记，且 Bot
   返回结果。
6. 前台测试通过后，向导将它改为后台常驻，并再次检查状态。

### 已经有 Bot：先看它是否已经在线

如果 Bot 已经通过 `lark-channel-bridge` 连着一台电脑，不要在另一处再次绑定相同应用。
先在飞书私聊发送 `/status`，找到它背后的 Agent 和 profile；把 `cyber-bookhouse` Skill
安装到那个 Agent，再发送“检查书屋”和一条真实的“同步笔记：链接”。现有 Bot 还承担
其他工作时，不必把默认工作目录改成 Obsidian 仓库。

### 已有应用但尚未连接：绑定 PersonalAgent

普通 Webhook 群机器人不能直接复用。现有 Bot 必须是飞书开放平台中的 PersonalAgent
应用，并且你有权查看它的 App ID 和 App Secret。

1. 在飞书开放平台“凭证与基础信息”中复制 App ID。
2. 向导运行：

```bash
lark-channel-bridge run \
  --profile cyber-bookhouse \
  --agent codex \
  --workspace "<你的书屋目录>" \
  --app-id cli_xxx
```

3. 只在本机终端的隐藏输入提示里填写 App Secret；不要把它写进命令或聊天。
4. 如果连接失败，按命令给出的官方页面检查 Bot 能力、发布/启用状态、可用范围及缺失
   权限，不手填猜测的 scope。
5. 仍然必须完成 `/status` 和真实 `同步笔记：链接` 两次验收。

前台验证后使用：

```bash
lark-channel-bridge start --profile cyber-bookhouse
lark-channel-bridge status --profile cyber-bookhouse
```

默认只有应用创建者可用。需要给同事私聊使用时发送 `/invite user @某人`；需要开放
当前群时，在群里发送 `/invite group`。群聊默认必须真正 @Bot。

飞书 Bot 只是输入入口。若还要把笔记生成飞书文档副本，需要另做 `lark-cli` 用户授权
和测试文档读回；接好 Bot 不等于已经取得个人云盘或文档权限。

## 接下来会发生什么

向导会依次做这几件事：

1. 找到或新建一个 Obsidian 书屋。新建时使用上表对应的英文磁盘目录，
   中文“赛博书屋”用于欢迎页和提示。
2. 识别当前运行 Skill 的桌面 Agent 是 Codex、Claude 还是 WorkBuddy。
3. Codex 与 WorkBuddy 接好各自手机端；Claude 需要手机入口时再接飞书或微信助理。
4. 从当前路线要求的每个入口各发一次测试链接。
5. 基础测试完成后，再问你只用当前工具，还是增加飞书入口或微信助理；
   Codex 与 Claude 用户也能由当前 Agent 引导微信助理绑定，还可以选择飞书文档输出。
6. 在 Obsidian 里打开结果给你看。
7. 如果选择飞书文档，再创建并读回一份测试文档；只创建成功不算接通。
8. 运行包内能力检查，区分可直接处理、需要浏览器和需要用户文件的内容。
9. 告诉你“同步笔记、蒸馏笔记、详细拆解”三种日常命令。

新建目录后，向导会先通过 Obsidian 的“打开文件夹作为仓库”完成注册，
再打开欢迎笔记。注册前不会直接调用 `obsidian://open?path=...`，否则
Obsidian 会提示 `Vault not found`。

它不会让你把密码、Token、App Secret、Cookie 或私人文档贴进对话。
需要登录、扫码或授权时，它只会把你带到对应软件自己的界面。
