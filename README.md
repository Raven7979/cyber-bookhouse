# 赛博三味书屋

把桌面 Agent、飞书或微信里的链接和文件，沉淀进同一个本地
Obsidian 知识库。

![赛博三味书屋项目总览](assets/screenshots/01-overview.png)

完全没接触过 Skill 的用户，从[第一次安装](INSTALL.md)开始。

首版安装包从
[GitHub Releases](https://github.com/Raven7979/cyber-sanwei/releases/latest)
下载。第三方软件不包含在安装包内，请使用本文提供的官方链接安装。

## 先选一条路线

| 路线 | 电脑端 | 手机端 | 本地知识库 |
| --- | --- | --- | --- |
| A | Codex | 不接手机 | Obsidian |
| B | Codex | 飞书 | Obsidian |
| C | WorkBuddy | 不接手机、飞书或微信三选一 | Obsidian |

Codex 接飞书使用开源的 Lark Channel Bridge。微信入口目前只走
WorkBuddy 官方的微信助理，不宣称 Codex 原生支持微信。

![三条安装路线示意](assets/screenshots/02-install-routes.png)

## 普通用户怎么开始

1. 安装 [Obsidian](https://obsidian.md/download)。
2. 选择并安装 [WorkBuddy](https://www.codebuddy.cn/work/) 或带 Codex
   模式的 [ChatGPT 桌面应用](https://chatgpt.com/download/)。
3. 下载本项目发布的 `sanwei` Skill：
   - WorkBuddy：进入「技能」，点「添加技能」→「上传技能」。
   - Codex：把 `sanwei` 文件夹交给 Codex，让它安装为本地 Skill。
4. 对桌面 Agent 说：

> 请使用 sanwei Skill，一步一步帮我搭好赛博三味书屋。先让我选择
> Codex 或 WorkBuddy，再选择只用桌面、接飞书或接微信。每次只告诉我
> 一个操作，最后要真实测试笔记进入 Obsidian。

向导会逐项检查软件、创建或选择知识库、连接所选手机渠道、配置后台
运行，并完成真实测试。第三方软件均从官方来源安装，本项目不打包其
安装程序。

安装完成后，在桌面 Agent 或飞书里发送：

> 收进书屋：https://example.com

下图是脱敏后的操作示意，不是真实用户账户或产品官方截图：

![从手机消息到本地笔记的处理过程](assets/screenshots/03-capture-example.png)

处理完成后，笔记在 Obsidian 中保留来源、采集方式、内容状态和转写
状态。拿不到的内容会明确标记，不会用标题或封面冒充正文。

![Obsidian 入库结果示意](assets/screenshots/04-obsidian-result.png)

## 支持的内容来源

| 内容类型 | 平台 |
| --- | --- |
| 播客、音频 | 小宇宙、Apple Podcasts、Spotify、公开 RSS、本地音频 |
| 长视频 | B站、YouTube、本地视频 |
| 短视频 | 抖音、视频号、小红书、快手、微博视频 |
| 图文 | 微信公众号、知乎、小红书、今日头条、百家号、搜狐号、微博、普通网页 |
| 文档 | 飞书文档、公开 Notion、PDF、Word、Markdown、TXT、PPT |

这里的“支持”表示能接收链接或文件，并按照实际访问能力沉淀笔记，
不表示无条件下载平台媒体。公开正文或用户提供的文件可以直接处理；
需要登录、没有字幕或受到平台限制时，向导会改用用户授权浏览器、
官方导出、用户提供文件或仅保存来源信息。详细边界写在
[`content-platforms.md`](skills/sanwei/references/content-platforms.md)。

## 完成标准

- 桌面 Agent 能创建一篇笔记。
- 如果选择了飞书或微信，手机端能收到处理回复。
- 所有已选择入口的笔记进入同一个 Obsidian vault。
- 在 Obsidian 中能看到正文和本地素材。
- 电脑重新登录后，所选远程连接能恢复。

电脑关机、深度睡眠或离线时，飞书和微信都无法调用本机 Agent。

## 平台边界

第一版安装向导先支持 macOS。桥接工具和部分应用也支持 Windows 或
Linux，但在向导完成跨平台实测前，不把它们标成已支持。

内容采集不绕过登录、验证码、付费墙、DRM、访问频率限制或平台权限，
也不把“只有标题和链接”冒充成完整内容。

## 当前状态

`v0.1.0` 是首个公开预览版：完成了 macOS 安装向导、Codex /
WorkBuddy 路线、飞书 / 微信入口选择、Obsidian 入库规范和内容平台
边界。各内容平台仍需继续逐个完成真实样本验收。
