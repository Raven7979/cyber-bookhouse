# WorkBuddy 安装路线

用户选择 WorkBuddy 时，按下面顺序完成。基础路线由电脑端和 WorkBuddy
移动端组成；飞书、微信助理是可选的额外入口。

## 安装顺序

1. 运行 `doctor`，只从 `software-links.md` 中的官方地址补装缺少的软件。
2. 确认「赛博书屋」已经出现在 WorkBuddy 的已安装技能中并处于启用
   状态。
3. 运行 `setup_state.py init --agent workbuddy --channel desktop`。此时不要
   询问飞书或微信助理，也不要把 `desktop` 换成其他值。
4. 新建书屋时，macOS 使用 `~/Documents/cyber-bookhouse`，Windows
   使用 `%USERPROFILE%\Documents\cyber-bookhouse`。按
   [obsidian.md](obsidian.md) 在 Obsidian 中选择“打开文件夹作为仓库”；
   不要用 `obsidian://open?path=...` 注册新仓库。
5. 打开 `欢迎来到赛博书屋.md`，确认文字在 Obsidian 里可见。
6. 用书屋路径作为证据，标记 `vault_registered`。
7. 在电脑上的 WorkBuddy 中发送
   `同步笔记：<你自己的一条文章、视频或播客链接>`。
8. 打开生成的笔记，确认原链接和正文可见，再标记 `desktop_test`。

## 接好 WorkBuddy 手机端

1. 按 WorkBuddy 当前官方界面登录移动端并连接电脑上的 WorkBuddy。
2. 不要猜测当前版本的菜单名；界面有变化时，以应用内引导或官方帮助为准。
3. 手机端能看到电脑任务后，标记 `mobile_connected`。证据不记录手机号、
   设备名或账号信息。
4. 从手机发送 `同步笔记：<你自己的一条内容链接>`。
5. 确认手机收到回复，而且笔记进入同一个 Obsidian 书屋，再标记
   `mobile_test`。

官方说明：
https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Practice-Cases/Practice-Six

## 基础测试通过后再选择入口

只有 `vault_registered`、`desktop_test`、`mobile_connected` 和
`mobile_test` 都完成后，才问：

> 基础书屋已经装好。你要只用 WorkBuddy，还是再接飞书或微信助理？

根据回答运行 `setup_state.py set-channel --channel desktop|feishu|wechat`。
不要在安装开始时提这个问题。

## 如果用户选择飞书或微信助理

1. 微信助理读取 [wechat-assistant.md](wechat-assistant.md)，按当前官方指南
   逐步扫码绑定；飞书按当前官方指南完成授权。
2. 不要用普通微信 App 图标或“微信机器人”泛称替代产品里的“微信助理”。
3. 登录、扫码和授权都由用户在官方界面中完成，不要求用户把凭据贴进
   对话。
4. 打开 WorkBuddy 的登录时启动，并在重启 WorkBuddy 后确认连接仍然可用。
5. 用不含账号信息的状态摘要标记 `channel_connected`。
6. 从选定入口发送 `同步笔记：<你自己的一条内容链接>`。
7. 确认入口收到回复，而且笔记进入同一个 Obsidian 书屋，再标记
   `channel_test`。

最后运行 `status`。全部完成后读取 [commands.md](commands.md)，把三种笔记
命令直接发给用户。第一次真实采集前再运行 `dependency_doctor.py`，按
[capabilities.md](capabilities.md) 报告当前电脑真正具备的能力。

电脑关机、深度睡眠、断网或 WorkBuddy 没有运行时，手机和额外入口都无法
继续调用这台电脑上的 WorkBuddy。
