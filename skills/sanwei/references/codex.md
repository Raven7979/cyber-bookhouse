# Codex 安装路线

用户选择 Codex 时，按下面顺序完成。基础路线由电脑上的 Codex 和手机上的
ChatGPT 组成；飞书是可选的额外入口。

## 安装顺序

1. 运行 `doctor`。只用电脑和手机时，Codex 桌面应用或 Codex CLI 均可。
   如果还要接飞书，需要已安装并登录 Codex CLI。
2. 运行 `setup_state.py init --agent codex --channel desktop`。用户明确要接
   飞书时，把 `desktop` 换成 `feishu`。
3. 在 Obsidian 中打开配置好的笔记文件夹。
4. 打开 `欢迎来到赛博三味书屋.md`，确认文字在 Obsidian 里可见。
5. 用书屋路径作为证据，标记 `vault_registered`。
6. 在电脑上的 Codex 中发送 `收进书屋：https://example.com`。
7. 打开生成的笔记，确认原链接和正文可见，再标记 `desktop_test`。

## 接好 ChatGPT 手机端

1. 让用户更新电脑上的 Codex 和手机上的 ChatGPT，并登录同一个 ChatGPT
   账号。
2. 按 OpenAI 当前界面，从 ChatGPT 手机端进入可远程访问的 Codex 任务。
   该功能可能仍处于逐步开放状态；不要编造用户当前版本里不存在的菜单。
3. 手机端能看到电脑任务后，标记 `mobile_connected`，证据只写
   “ChatGPT mobile connected”，不要记录账号、设备名或会话 ID。
4. 从手机发送 `收进书屋：https://example.com`。
5. 确认手机收到回复，并在同一个 Obsidian 书屋里看到新笔记，再标记
   `mobile_test`。

官方说明：
https://openai.com/index/work-with-codex-from-anywhere/

## 如果用户还要接飞书

1. 确认 Node.js 20.12.0 或更高版本已安装。
2. 从官方包安装桥接工具：`npm install -g lark-channel-bridge`。
3. 运行 `lark-channel-bridge run --agent codex`。
4. 让用户在官方界面扫码并完成飞书授权，不要要求用户把 App Secret
   贴进对话。
5. 前台测试正常后停止它，再运行
   `lark-channel-bridge start --agent codex`。
6. 确认 `lark-channel-bridge status` 显示后台服务正常，再标记
   `channel_connected`。
7. 在飞书中发送 `收进书屋：https://example.com`。
8. 确认飞书收到回复，而且笔记进入同一个 Obsidian 书屋，再标记
   `channel_test`。

电脑关机、深度睡眠或断网时，手机和飞书都无法继续调用这台电脑上的
Codex。接了飞书时，后台桥接必须能在电脑重新登录后恢复，不能要求用户
一直开着终端窗口。
