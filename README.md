# 赛博三味书屋

刷到一段好视频、听到一期播客、看到一篇长文，当时觉得有用，过几天却
怎么也找不到了。

赛博三味书屋想解决的就是这件小事：把链接发给你平时用的 ChatGPT 或
WorkBuddy，电脑把能读到的内容整理好，连同来源、摘要、截图和转写一起
放进 Obsidian。Codex 用户如果愿意授权，也可以再生成一份飞书文档。
以后想找，不必再翻聊天记录和收藏夹。

![赛博三味书屋项目总览](assets/screenshots/01-overview.png)

它不是一个新的笔记软件，也不是在线内容平台。它是一套可以交给桌面
Agent 安装的 Skill；本地原件仍放在你自己的 Obsidian 里。

## 下载包里有什么

`sanwei.zip` 不再只是一份安装说明。包内包含：

- 安装状态、入口连接和真实测试记录；
- 依赖能力检查，能区分“软件存在”和“这条链接真的能读取”；
- 普通公开网页正文读取，以及需要授权时的可见页面降级；
- YouTube 公开字幕采集与真人验证降级；
- 本地音视频信息、代表帧和本地语音转写调用；
- 标准笔记、方法蒸馏、详细拆解和失败边界；
- Obsidian、飞书文档及各入口的写入和读回验收。

它不依赖维护者电脑上的私人 Skill。`yt-dlp`、FFmpeg、Obsidian 和飞书工具
仍从各自官方来源安装，项目不把第三方程序塞进压缩包。当前电脑缺少什么，
向导会检查后只给对应的官方链接。

## 先选你已经在用的那个

| 你平时用什么 | 电脑上 | 手机上 | 还可以接 |
| --- | --- | --- | --- |
| ChatGPT / Codex | Codex | ChatGPT 手机端 | 飞书入口、飞书文档 |
| WorkBuddy | WorkBuddy | WorkBuddy 手机端 | 飞书、微信 |

已经在用 ChatGPT，就走 Codex 这条路；已经在用 WorkBuddy，就走
WorkBuddy。不用为了这套书屋把两边都装一遍。

Codex 可以从 ChatGPT 手机端查看和继续电脑上的任务；WorkBuddy 也有自己
的移动端远程入口。飞书和微信是额外入口，不是手机使用的前提。具体可看
[OpenAI 的 Codex 手机端说明](https://openai.com/index/work-with-codex-from-anywhere/)
和
[WorkBuddy 的移动端远程说明](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Practice-Cases/Practice-Six)。

![Codex 从电脑、手机或飞书接收内容，再写入 Obsidian 或飞书文档](assets/screenshots/02-codex-route.png)

Codex 默认把 Markdown 原件写入本地 Obsidian；完成飞书官方授权和真实
读回测试后，也可以同时生成飞书文档副本。飞书入口和飞书文档是两件事：
前者负责“从哪里发”，后者负责“整理后放到哪里”。
飞书文档能力使用[飞书官方 Lark / Feishu CLI](https://github.com/larksuite/cli)，
本项目不打包该工具。

![WorkBuddy 电脑端、手机端、飞书和微信进入 Obsidian 书屋的路线](assets/screenshots/03-workbuddy-route.png)

手机也可以作为单独入口：

![从 ChatGPT 或 WorkBuddy 手机端发送内容链接，经电脑 Agent 写入 Obsidian](assets/screenshots/06-mobile-route.png)

如果还要增加常用入口，飞书和微信分别走下面两条路：

![从飞书发送内容链接，经 Codex 或 WorkBuddy 写入 Obsidian](assets/screenshots/07-feishu-route.png)

![从微信发送内容链接，经 WorkBuddy 写入 Obsidian](assets/screenshots/08-wechat-route.png)

## 第一次怎么装

1. 安装 [Obsidian](https://obsidian.md/download)。
2. 安装你选择的桌面工具：
   [Codex / ChatGPT](https://chatgpt.com/download/) 或
   [WorkBuddy](https://www.codebuddy.cn/work/)。
3. 从 [Releases](https://github.com/Raven7979/cyber-sanwei/releases/latest)
   下载 `sanwei.zip`。
4. 按[第一次安装](INSTALL.md)把 Skill 交给 Codex 或 WorkBuddy。
5. 对它说：

> 请用 sanwei Skill 帮我搭好赛博三味书屋。请识别我当前使用的是 Codex
> 还是 WorkBuddy，先完成软件、Obsidian 和手机测试，之后再问我要不要增加
> 飞书入口、微信或飞书文档。每次只说一个操作，最后请用真实测试确认手机
> 和电脑都能把笔记写进 Obsidian；如果我选择飞书文档，也要创建并读回一份
> 测试文档。基础测试完成后，请运行包内的能力检查，告诉我哪些内容能直接
> 处理、哪些需要浏览器授权或本地文件。

软件安装程序都从各自官网下载安装，这个仓库不重新打包。

第一次安装时，它会帮你选好 Obsidian 文件夹、接通手机入口，再用一个
示例链接做测试。新建书屋的磁盘目录使用英文名
`~/Documents/cyber-sanwei`，在欢迎页和操作提示中仍称为“赛博三味书屋”。
看到测试笔记真的出现在 Obsidian 里，才算装完。

向导会先把基础书屋和手机端完整测通，之后才问是否增加飞书入口、微信或
飞书文档，不会在安装开始时用路线选择打断流程。

## 平时怎么用

全部安装完成后，向导会给出三种命令。在 ChatGPT、Codex、WorkBuddy、飞书
或微信中，把链接或文件发出去，并说：

> 同步笔记：`https://www.bilibili.com/video/BV1xxxxxxxxx`

- `同步笔记`：视频做简单总结、逐字稿和必要的翻译；图文做正文总结。
  适合学习、记录和留档。
- `蒸馏笔记`：做详细的结构、表达和方法分析，重点适合短片拉片。
- `详细拆解`：完整包含“同步笔记”和“蒸馏笔记”的所有内容。

`收进书屋：链接` 仍然可以使用，等同于“同步笔记”。

![同一条内容链接可选择同步笔记、蒸馏笔记或详细拆解](assets/screenshots/05-note-modes.png)

### 有结构的内容，会适当配图

原文或视频里确实有 SOP、前后依赖、多条分支、方法框架或明显的叙事节奏时，
书屋可以自动生成同一套视觉风格的 SVG 图片和本地 HTML 大图，插在对应的笔记段落中。

- 同步笔记：只有原内容明确有流程或框架时才画，最多 1 张。
- 蒸馏笔记：遇到流程、分支、框架或短片节奏时，可以画 1-3 张。
- 详细拆解：完整使用前两种笔记中最有信息量的图，不重复画同一关系。

![结构化 SOP 会自动生成可嵌入 Obsidian 的流程图](assets/screenshots/09-structured-visuals.svg)

只有 1-2 步、证据不足或节点之间没有真实关系时，不会为了好看硬塞一张图。
图后仍会保留文字说明，便于搜索和回到原文复核。

整理完成后，Obsidian 里的笔记会保留来源、采集时间、正文状态和转写
状态。选择飞书文档的 Codex 用户还会得到一份经过读回验收的飞书副本。
哪部分没有拿到，会直接写明白，不会拿标题和封面凑一篇“完整总结”。

## 能整理哪些内容

![支持的长视频、短视频、播客、图文和文档平台](assets/screenshots/04-platforms.png)

| 内容类型 | 常见来源 |
| --- | --- |
| 播客、音频 | 小宇宙、Apple Podcasts、Spotify、公开 RSS、本地音频 |
| 长视频 | B站、YouTube、本地视频 |
| 短视频 | 抖音、视频号、小红书、快手、微博视频、X 视频 |
| 图文 | 微信公众号、知乎、小红书、今日头条、百家号、搜狐号、微博、X、普通网页 |
| 文档 | 飞书文档、公开 Notion、PDF、Word、Markdown、TXT、PPT |

这里的“能整理”不等于“任何链接都能完整下载”。公开页面和你自己提供的
文件通常可以直接处理；遇到登录、付费内容、没有字幕或平台限制时，它会
告诉你缺了什么，并让你选择授权浏览器、官方导出或自己提供文件。更细的
边界写在[内容平台说明](skills/sanwei/references/content-platforms.md)里。

例如 YouTube 出现“确认你不是机器人”时，向导会停止重复抓取，只询问是否
授权读取已登录页面上可见的字幕；不会自动导出浏览器 Cookie。拒绝授权也
没关系，已有元数据会保留，逐字稿明确标成未取得。

平台名称和 Logo 仅用于说明兼容入口，权利归各自持有人所有。

## 什么样才算真的装好了

- 电脑端发一个测试链接，Obsidian 里出现可读的笔记。
- 手机端也能继续同一个工作，并收到处理结果。
- 如果另外接了飞书或微信，它们写入的是同一个 Obsidian 书屋。
- 如果选择了飞书文档，测试文档能创建、能读回，链接能由用户打开。
- 笔记里的来源、正文、图片或视频截图能够正常打开。
- 包内能力检查已运行，缺少的外部工具和受限平台被如实报告。
- 电脑重新登录后，不需要重新从头配置。

手机远程入口依赖电脑在线。电脑关机、深度睡眠或断网时，本机 Agent
无法继续处理新内容。

## 有几件事先说清楚

- 第一版安装向导先按 macOS 做了完整测试。
- 不绕过登录、验证码、付费墙、DRM、访问频率限制或平台权限。
- 不要求你把密码、Token、Cookie、私人文档或 Obsidian 库交给项目维护者。
- 只能拿到标题和链接时，就只保存标题和链接，不假装已经看过正文或视频。

隐私细节见 [PRIVACY.md](PRIVACY.md)，安全问题见
[SECURITY.md](SECURITY.md)。

## 现在做到哪一步

`v0.1.2` 是第一个公开版本。macOS 安装向导、Codex / WorkBuddy、
手机入口、飞书 / 微信选项、Codex 的飞书文档输出、Obsidian 笔记格式和
内容边界已经放进仓库。
不同内容平台仍需要继续拿真实样本逐个测试。
