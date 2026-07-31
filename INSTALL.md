# 第一次安装

Skill 还没安装时，它无法自己说话。因此第一次只需要人工完成“把 Skill
放进桌面 Agent”这一件事；从下一句话开始，所有步骤都由它逐项引导。

## WorkBuddy

1. 安装并打开 [WorkBuddy](https://www.codebuddy.cn/work/)。
2. 打开「技能」，点击「添加技能」→「上传技能」。
3. 选择发布页下载的 `sanwei.zip`。
4. 确认「赛博三味书屋」显示在已安装技能中并处于启用状态。
5. 新建一个任务，发送：

> 请使用 sanwei Skill，一步一步帮我搭好赛博三味书屋。每次只告诉我
> 一个操作，做完再继续。

官方说明：[WorkBuddy 技能安装](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)。

## Codex

1. 安装并打开带 Codex 模式的
   [ChatGPT 桌面应用](https://chatgpt.com/download/)；已有 Codex CLI
   的用户也可以直接使用。
2. 解压发布页下载的 `sanwei.zip`。
3. 把解压后的 `sanwei` 文件夹拖进 Codex 对话，并发送：

> 请把这个 sanwei 文件夹安装为我的用户级 Skill。安装到
> ~/.agents/skills/sanwei，回读 SKILL.md 并确认 /skills 中能看到
> sanwei；不要改动我已有的其他 Skills。

4. 安装确认后发送：

> 请使用 $sanwei，一步一步帮我搭好赛博三味书屋。每次只告诉我一个
> 操作，做完再继续。

Codex 官方会从 `~/.agents/skills` 读取用户级 Skill；若未立即出现，
重启 Codex 后再检查。

## 向导会问什么

它只会依次问：

1. 使用 Codex 还是 WorkBuddy；
2. 使用现有 Obsidian vault 还是新建一个；
3. 只用电脑，还是再接飞书或微信；
4. 当前这一步是否已经在界面中完成。

它不会要求用户把密码、Token、App Secret 或 Cookie 发进对话。
