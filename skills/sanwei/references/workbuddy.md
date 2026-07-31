# WorkBuddy 安装路线

用户选择 WorkBuddy 时，按下面顺序完成。基础路线由电脑端和 WorkBuddy
移动端组成；飞书、微信是可选的额外入口。

## 安装顺序

1. 运行 `doctor`，只从 `software-links.md` 中的官方地址补装缺少的软件。
2. 确认「赛博三味书屋」已经出现在 WorkBuddy 的已安装技能中并处于启用
   状态。
3. 运行 `setup_state.py init --agent workbuddy --channel desktop`。用户
   明确要接飞书或微信时，把 `desktop` 换成对应选项。
4. 在 Obsidian 中打开配置好的笔记文件夹。
5. 打开 `欢迎来到赛博三味书屋.md`，确认文字在 Obsidian 里可见。
6. 用书屋路径作为证据，标记 `vault_registered`。
7. 在电脑上的 WorkBuddy 中发送 `收进书屋：https://example.com`。
8. 打开生成的笔记，确认原链接和正文可见，再标记 `desktop_test`。

## 接好 WorkBuddy 手机端

1. 按 WorkBuddy 当前官方界面登录移动端并连接电脑上的 WorkBuddy。
2. 不要猜测当前版本的菜单名；界面有变化时，以应用内引导或官方帮助为准。
3. 手机端能看到电脑任务后，标记 `mobile_connected`。证据不记录手机号、
   设备名或账号信息。
4. 从手机发送 `收进书屋：https://example.com`。
5. 确认手机收到回复，而且笔记进入同一个 Obsidian 书屋，再标记
   `mobile_test`。

官方说明：
https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Practice-Cases/Practice-Six

## 如果用户还要接飞书或微信

1. 打开 WorkBuddy 的助理设置，选择用户要用的入口。
2. 微信按当前官方微信助理指南扫码绑定；飞书按当前官方指南完成授权。
3. 登录、扫码和授权都由用户在官方界面中完成，不要求用户把凭据贴进
   对话。
4. 打开 WorkBuddy 的登录时启动，并在重启 WorkBuddy 后确认连接仍然可用。
5. 用不含账号信息的状态摘要标记 `channel_connected`。
6. 从选定入口发送 `收进书屋：https://example.com`。
7. 确认入口收到回复，而且笔记进入同一个 Obsidian 书屋，再标记
   `channel_test`。

电脑关机、深度睡眠、断网或 WorkBuddy 没有运行时，手机和额外入口都无法
继续调用这台电脑上的 WorkBuddy。
