# WorkBuddy 微信助理绑定

微信入口使用的是 WorkBuddy 的“微信助理”，不是普通微信 App 图标，也
不是 Codex 自己直接接收微信消息。无论安装向导当前运行在 WorkBuddy 还是
Codex，只要用户在基础测试完成后主动选择微信，就按本页继续引导。

官方指南：
https://www.codebuddy.cn/docs/workbuddy/WeixinBot-Guide

## 开始前

1. 重新打开上面的官方指南，核对当前版本要求和界面。当前官方要求为
   WorkBuddy 4.6.4 或更高版本、微信 8.0.70 或更高版本。
2. 确认手机已经登录微信，电脑能够联网并保持 WorkBuddy 运行。
3. 微信助理只需扫码绑定，不需要 App ID、App Secret、Token 或 webhook。
4. 登录、扫码和账号确认由用户在 WorkBuddy 与微信的官方界面完成。不要
   让用户把二维码、手机号、账号名或凭据贴进对话。

## 如果当前向导运行在 Codex

1. 如果电脑没有 WorkBuddy，只从
   [software-links.md](software-links.md) 的官方地址安装。
2. 在 WorkBuddy 的“技能”里上传同一份 `sanwei.zip`，确认“赛博三味书屋”
   已启用。
3. 让 WorkBuddy 读取现有配置和书屋路径；不要再次运行 `init`，不要新建
   第二个 Obsidian 仓库，也不要改变当前 Codex 与 ChatGPT 手机端的基础
   测试记录。
4. 明确告诉用户：Codex 正在负责引导；微信消息真正进入的是 WorkBuddy
   微信助理，二者最后写入同一个 Obsidian 书屋。

## 一步一步绑定

每次只给用户一个操作，完成后再继续：

1. 打开 WorkBuddy 的“助理”。优先点击助理栏的齿轮进入“助理设置”；
   当前版本如果没有该齿轮，则点击左下角头像，再进入“设置 → 助理设置”。
2. 在集成列表找到“微信助理集成”，点击“配置”。
3. 等待二维码出现。按钮短暂显示“绑定中...”属于正常生成过程。
4. 让用户用手机微信扫描二维码。二维码过期时，重新点击“配置”或“重试”
   生成新的二维码。
5. 回到 WorkBuddy，只有卡片显示“已绑定”后，才记录
   `channel_connected`。证据只写 `WorkBuddy WeChat Assistant: bound`，
   不记录微信账号。

记录连接状态：

```bash
<python-command> "<skill-dir>/scripts/setup_state.py" mark \
  --step channel_connected --status complete \
  --evidence "WorkBuddy WeChat Assistant: bound"
```

## 真实回测

1. 从刚绑定的微信助理发送：
   `同步笔记：<用户自己的一条公开文章、视频或播客链接>`。
2. 确认微信收到 WorkBuddy 的处理回复。
3. 在 Obsidian 中打开新笔记，确认原始链接和正文写入当前同一个书屋。
4. 三项都通过后再记录 `channel_test`。只看到“已绑定”不算测试完成。

```bash
<python-command> "<skill-dir>/scripts/setup_state.py" mark \
  --step channel_test --status complete \
  --evidence "WECHAT_REPLY_AND_OBSIDIAN_NOTE_PATH"
```

## 常见失败

- 一直显示“绑定中...”：关闭配置窗口，重新进入微信助理集成；仍失败时
  重启 WorkBuddy 再绑定。
- 扫码后没有“已绑定”：等待几秒；二维码过期就重新生成。
- 微信里没有回复：确认 WorkBuddy 仍在运行、网络正常，并回到助理设置
  检查状态是否仍为“已绑定”。必要时解绑后重新扫码。
- 电脑关机、深度睡眠、断网或 WorkBuddy 退出时，微信助理无法继续调用
  这台电脑。
