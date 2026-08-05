# Claude 安装路线

用户选择 Claude Code 时，先完成电脑端与 Obsidian 的真实写入测试。Claude
路线不把未经核实的 Claude 手机端能力当成基础条件；需要手机入口时，使用
已经回测过的飞书桥接，或由 WorkBuddy 微信助理接入同一个书屋。

## 安装顺序

1. 运行 `doctor`，确认 `claude` 命令或 Claude 桌面应用与 Obsidian 可用。
2. 运行 `setup_state.py init --agent claude --channel desktop`。
3. 新建书屋时，macOS 使用 `~/Documents/cyber-sanwei`，Windows 使用
   `%USERPROFILE%\Documents\cyber-sanwei`。按
   [obsidian.md](obsidian.md) 在 Obsidian 中选择“打开文件夹作为仓库”。
4. 打开 `欢迎来到赛博书屋.md`，确认文字在 Obsidian 中可见。
5. 用书屋路径作为证据，标记 `vault_registered`。
6. 在 Claude 中发送 `同步笔记：<你自己的一条文章、视频或播客链接>`。
7. 打开生成的笔记，确认原链接和正文可见，再标记 `desktop_test`。

Claude 的基础路线只有电脑端；初始化脚本会把两个手机客户端步骤记录为
“此路线不要求”。这不代表手机已经接通。用户选飞书或微信助理后，仍必须
从该入口发送真实链接，并验证回复与同一 Obsidian 书屋中的新笔记。

## 基础测试后选择入口

电脑端测试通过后问：

> 基础书屋已经装好。你要只用 Claude，还是再接飞书入口、微信助理或飞书
> 文档？

根据回答运行 `setup_state.py set-channel --channel desktop|feishu|wechat`。
只选择飞书文档时，输入通道仍是 `desktop`。

## 如果用户选择飞书入口

飞书入口由开源的 `lark-channel-bridge` 把消息交给本机 Claude Code。只从
[software-links.md](software-links.md) 指向的官方仓库和 npm 包安装。

1. 确认 Node.js 20.12.0 或更高版本，以及已登录的 `claude` 命令。
2. 运行 `npm install -g lark-channel-bridge`。
3. 运行：

```bash
lark-channel-bridge run --profile claude --agent claude --workspace "<vault>"
```

4. 让用户在飞书官方界面扫码并完成 PersonalAgent 绑定。不要要求用户把
   App Secret、二维码或 Token 贴进对话。
5. 只保留创建者本人默认可用的私有范围；用户没有明确要求时，不邀请其他
   用户或群，不开放群访问。
6. 前台测试正常后停止它，再运行：

```bash
lark-channel-bridge start --profile claude --agent claude --workspace "<vault>"
lark-channel-bridge status --profile claude
```

7. 在飞书中发送 `同步笔记：<你自己的一条内容链接>`。
8. 确认飞书收到回复，而且笔记进入同一个 Obsidian 书屋，再标记
   `channel_connected` 和 `channel_test`。

## 如果用户选择微信助理

读取 [wechat-assistant.md](wechat-assistant.md)，由 Claude 一步一步完成：

1. 缺少 WorkBuddy 时从官方地址安装。
2. 在 WorkBuddy 上传同一份 `cyber-bookhouse.zip`，读取现有书屋路径，不重新建库。
3. 打开“微信助理集成”，让用户在官方界面扫码，确认显示“已绑定”。
4. 从微信发送真实测试链接，确认微信收到回复，而且笔记进入当前同一个
   Obsidian 书屋。

不要说成 Claude 直接接收微信消息。Claude 负责引导与现有书屋，WorkBuddy
微信助理负责微信入口。

## 如果用户选择飞书文档

按 [feishu-docs.md](feishu-docs.md) 配置。必须先在 Obsidian 留下本地原件，
再创建飞书文档副本并读回验收。创建成功但无法读回，不算接通。

最后运行 `status`。全部完成后读取 [commands.md](commands.md)，把三种笔记
命令直接发给用户。第一次真实采集前再运行 `dependency_doctor.py`，按
[capabilities.md](capabilities.md) 报告当前电脑真正具备的能力。

电脑关机、深度睡眠或断网时，飞书、微信助理和飞书文档写入都无法继续调用
这台电脑上的 Claude。接了飞书入口时，后台桥接必须能在电脑重新登录后恢复。
