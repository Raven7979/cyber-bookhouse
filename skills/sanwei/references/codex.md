# Codex 安装路线

用户选择 Codex 时，按下面顺序完成。基础路线由电脑上的 Codex 和手机上的
ChatGPT 组成；飞书可以是额外入口，飞书文档也可以是授权后的额外输出。
本地 Obsidian 始终保留一份可迁移的 Markdown 原件。

## 安装顺序

1. 运行 `doctor`。只用电脑和手机时，Codex 桌面应用或 Codex CLI 均可。
   如果还要接飞书，需要已安装并登录 Codex CLI。
2. 运行 `setup_state.py init --agent codex --channel desktop`。此时不要
   询问飞书，也不要把 `desktop` 换成其他值。
3. 新建书屋时，macOS 使用 `~/Documents/cyber-sanwei`，Windows
   使用 `%USERPROFILE%\Documents\cyber-sanwei`。按
   [obsidian.md](obsidian.md) 在 Obsidian 中选择“打开文件夹作为仓库”；
   不要用 `obsidian://open?path=...` 注册新仓库。
4. 打开 `欢迎来到赛博三味书屋.md`，确认文字在 Obsidian 里可见。
5. 用书屋路径作为证据，标记 `vault_registered`。
6. 在电脑上的 Codex 中发送
   `同步笔记：<你自己的一条文章、视频或播客链接>`。
7. 打开生成的笔记，确认原链接和正文可见，再标记 `desktop_test`。

## 接好 ChatGPT 手机端

1. 让用户更新电脑上的 Codex 和手机上的 ChatGPT，并登录同一个 ChatGPT
   账号。
2. 按 OpenAI 当前界面，从 ChatGPT 手机端进入可远程访问的 Codex 任务。
   该功能可能仍处于逐步开放状态；不要编造用户当前版本里不存在的菜单。
3. 手机端能看到电脑任务后，标记 `mobile_connected`，证据只写
   “ChatGPT mobile connected”，不要记录账号、设备名或会话 ID。
4. 从手机发送 `同步笔记：<你自己的一条内容链接>`。
5. 确认手机收到回复，并在同一个 Obsidian 书屋里看到新笔记，再标记
   `mobile_test`。

官方说明：
https://openai.com/index/work-with-codex-from-anywhere/

## 基础测试通过后再选择入口

只有 `vault_registered`、`desktop_test`、`mobile_connected` 和
`mobile_test` 都完成后，才问：

> 基础书屋已经装好。你要只用 Codex，还是再接飞书入口、飞书文档，或者
> 两者都接？

根据回答运行 `setup_state.py set-channel --channel desktop|feishu`。不要在
安装开始时提这个问题。只选择飞书文档时，输入通道仍是 `desktop`。

## 如果用户选择飞书

1. 确认 Node.js 20.12.0 或更高版本已安装。
2. 从官方包安装桥接工具：`npm install -g lark-channel-bridge`。
3. 运行 `lark-channel-bridge run --agent codex`。
4. 让用户在官方界面扫码并完成飞书授权，不要要求用户把 App Secret
   贴进对话。
5. 前台测试正常后停止它，再运行
   `lark-channel-bridge start --agent codex`。
6. 确认 `lark-channel-bridge status` 显示后台服务正常，再标记
   `channel_connected`。
7. 在飞书中发送 `同步笔记：<你自己的一条内容链接>`。
8. 确认飞书收到回复，而且笔记进入同一个 Obsidian 书屋，再标记
   `channel_test`。

## 如果用户选择飞书文档

输入入口测试完成后，再按 [feishu-docs.md](feishu-docs.md) 配置飞书文档。
必须先在 Obsidian 留下本地原件，再创建飞书文档副本，并把副本读回来验收。
创建成功但无法读回，不算接通。

验收通过后运行：

```bash
<python-command> "<skill-dir>/scripts/setup_state.py" set-destination \
  --destination obsidian-feishu \
  --evidence "CREATED_AND_READ_BACK_TEST_DOC_URL"
```

没有选择飞书文档时，运行 `set-destination --destination obsidian`。

最后运行 `status`。全部完成后读取 [commands.md](commands.md)，把三种笔记
命令直接发给用户。第一次真实采集前再运行 `dependency_doctor.py`，按
[capabilities.md](capabilities.md) 报告当前电脑真正具备的能力。

电脑关机、深度睡眠或断网时，手机、飞书入口和飞书文档写入都无法继续
调用这台电脑上的 Codex。接了飞书入口时，后台桥接必须能在电脑重新登录
后恢复，不能要求用户一直开着终端窗口。
