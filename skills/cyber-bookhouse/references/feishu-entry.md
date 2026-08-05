# 飞书 Bot 输入入口

飞书入口负责“从哪里发链接”，把飞书消息转给当前电脑上的 Codex 或 Claude；
Obsidian 仍然保存本地原件。飞书文档副本是另一条可选输出路线，按
[feishu-docs.md](feishu-docs.md) 单独授权和验收。

## 先确认基础路线

只有桌面 Agent、Obsidian 注册和桌面真实链接测试已经通过，才开始接飞书。
电脑关机、深度睡眠或断网时，本机 Agent 无法继续处理飞书的新消息。

先检查：

```bash
node --version
codex --version
# 或：claude --version
```

Node.js 必须达到 `20.12.0` 或更高，当前 Agent 必须已经登录。缺少软件时只从
[software-links.md](software-links.md) 的官方来源安装。

## 安装连接器

使用 `lark-channel-bridge` 把飞书 PersonalAgent 应用接到本机 Agent：

```bash
npm i -g lark-channel-bridge
lark-channel-bridge --version
lark-channel-bridge profile list
```

不要用 `npx` 安装后台服务。后台服务会记住可执行文件路径，npm 临时缓存被清理后
会导致服务失效。若已有同名 profile，不覆盖它；选择新的、不冲突的 profile 名。

## 路线 A：没有飞书 Bot，扫码创建

这是默认路线。以下示例使用 profile 名 `cyber-bookhouse`，Agent 必须按当前宿主替换
`codex` 或 `claude`，`<vault-path>` 替换为已经验收通过的书屋目录：

```bash
lark-channel-bridge run \
  --profile cyber-bookhouse \
  --agent codex \
  --workspace "<vault-path>"
```

接下来每次只让用户完成一个界面动作：

1. 终端出现二维码后，用飞书 App 扫码。
2. 在飞书官方页面选择或创建一个 PersonalAgent 应用。
3. 同意页面显示的权限和绑定操作。
4. 回到终端，等待出现“已连接”以及 Bot 名称。
5. 在飞书里找到刚创建的 Bot，先私聊发送 `/status`。

扫码向导会创建或绑定 PersonalAgent 应用，并把 profile 写入本机
`~/.lark-channel/`。不要要求用户把 App Secret、Token 或二维码内容贴进对话。

## 路线 B：已经有飞书 Bot

先判断这个 Bot 是否已经通过 `lark-channel-bridge` 连着一台电脑。不要让同一个飞书
应用同时连接两个 bridge 进程；它们会争抢同一个应用和消息连接。

### B1：已有 Bot 已经在线

1. 在飞书里私聊它发送 `/status`，确认背后是 Codex 或 Claude，并记住 profile 与
   当前工作目录。
2. 在那台电脑运行 `lark-channel-bridge profile list` 和对应 profile 的 `status`。
3. 把 `cyber-bookhouse` Skill 安装到这个 Bot 背后的同一个 Agent 用户环境；不要另建
   第二个 bridge。
4. 在 Bot 私聊发送“检查书屋”，让 Skill 读取现有书屋配置；若还没配置，就按基础
   onboarding 完成 Obsidian 设置。
5. 发送一条真实的“同步笔记：链接”，回读同一个 Obsidian 书屋和 Bot 回复。

如果现有 Bot 还承担其他工作，不必把它的默认工作目录改成 Obsidian 仓库。赛博书屋
使用自己的配置记录目标 vault。只有用户明确要做专用 Bot 时，才新建独立应用和 profile。

### B2：已有 PersonalAgent 应用，但还没有连接本机 Agent

先问清楚：它是否是飞书开放平台中的 PersonalAgent 应用，并且用户是否有权限查看
该应用的 App ID 和 App Secret。普通“群机器人 Webhook”不能直接作为这条入口；
这类机器人只有推送地址，没有 PersonalAgent 的消息会话与应用凭据。

如果已有 PersonalAgent 应用，在飞书开放平台的“凭证与基础信息”中只复制 App ID。
运行：

```bash
lark-channel-bridge run \
  --profile cyber-bookhouse \
  --agent codex \
  --workspace "<vault-path>" \
  --app-id cli_xxx
```

命令随后会在本机终端隐藏输入 App Secret。让用户直接在该提示中输入，不要把 Secret
作为 `--app-secret` 参数写进 shell 历史，也不要发到聊天中。Lark 国际版应用增加
`--tenant lark`。

如果现有应用无法连接，按命令返回的官方页面检查这四项，不猜权限名：

1. 应用已启用 Bot / PersonalAgent 能力；
2. 应用凭据属于当前租户且没有复制错；
3. 应用已发布或启用，当前用户在可用范围内；
4. 命令提示的消息权限或事件配置已经在飞书官方页面完成。

修正后重新前台运行，并以真实收发结果为准。服务“已启动”不等于用户一定能搜索到
Bot；发布状态和可用范围必须在飞书后台或实际账号中确认。

## 前台测试

连接成功后，在 Bot 私聊依次发送：

```text
/status
检查书屋
同步笔记：https://一个你熟悉的公开链接
```

验收同时满足：

1. `/status` 返回正确 profile、Agent 和工作目录；
2. Bot 收到链接后有明确回复，不是一直无响应；
3. 同一个 Obsidian 书屋中出现可读 Markdown 笔记；
4. 笔记保留来源、获取状态和未取得内容说明；
5. Bot 最终返回笔记路径或处理结果。

只有上述测试通过，才记录飞书入口：

```bash
<python-command> "<skill-dir>/scripts/setup_state.py" set-channel --channel feishu
<python-command> "<skill-dir>/scripts/setup_state.py" mark \
  --step channel_connected --status complete --evidence "PROFILE_AND_CONNECTED_STATUS"
<python-command> "<skill-dir>/scripts/setup_state.py" mark \
  --step channel_test --status complete --evidence "NOTE_PATH_AND_BOT_REPLY"
```

证据只记录 profile、状态、笔记路径和回复结果，不记录 App Secret、Token、聊天 ID 或
用户 ID。

## 改为后台常驻

前台实测通过后，先按 `Ctrl-C` 停止 `run`，再安装系统后台服务：

```bash
lark-channel-bridge start --profile cyber-bookhouse
lark-channel-bridge status --profile cyber-bookhouse
```

然后回到飞书再发一次 `/status`，确认后台模式仍能回复。macOS 使用 launchd，Linux
使用 systemd 用户服务，Windows 使用任务计划程序。排查时先运行：

```bash
lark-channel-bridge status --profile cyber-bookhouse
lark-channel-bridge ps
```

## 谁可以使用 Bot

默认只有创建或拥有该应用的人可以使用。个人使用不需要额外开放。需要给同事或群使用
时，由创建者或管理员在飞书中发送：

```text
/invite user @某人
/invite group
/invite admin @某人
```

私聊不需要 @Bot；群聊和话题群默认必须真正 @Bot。名单修改从下一条消息起生效，
无需重启。不要默认对所有成员开放；先用最小范围测试。

## 飞书 Bot 与飞书文档不要混为一谈

- 飞书 Bot：接收消息，把任务送到本机 Agent；使用应用身份，默认 `bot-only`。
- 飞书文档：把 Obsidian 原件发布成协作副本；需要另走 `lark-cli` 用户授权并读回。
- 已经接好 Bot，不代表自动拥有个人云盘或文档权限；需要文档副本时再读
  [feishu-docs.md](feishu-docs.md)。

## 常见问题

**飞书里搜不到 Bot。** 先检查应用是否已发布或启用、当前用户是否在可用范围内；
“bridge 已连接”不能替代这项检查。

**Bot 没有回复。** 先发 `/status`；再检查 Codex / Claude 是否登录、profile 工作目录
是否存在，以及电脑是否在线。必要时运行 `lark-channel-bridge status` 和
`lark-channel-bridge ps`。

**群里没有反应。** 确认真正 @ 了 Bot，并由创建者在该群发送 `/invite group`。

**已有的是 Webhook 群机器人。** 不复用该 Webhook；走“扫码创建”路线，或准备一个
能提供 App ID / App Secret 的 PersonalAgent 应用。

**已有 Bot 正在另一台电脑或服务器运行。** 不要在当前电脑再次绑定同一 App ID。
要么把 Skill 安装到原 Bot 背后的 Agent，要么创建一个新的 PersonalAgent 应用和独立
profile。
