# 飞书文档输出

飞书文档是 Codex 路线的可选发布副本，不替代 Obsidian 中的本地 Markdown
原件。只有用户主动选择，并在飞书官方页面完成授权后，才配置这条路线。

## 先说明边界

- 不把 App Secret、Token、验证码或私人文档内容贴进对话。
- 软件和 Skill 只从飞书官方维护的
  [larksuite/cli](https://github.com/larksuite/cli) 安装。
- 只申请创建和读取文档所需的权限；授权由用户在官方页面完成。
- 创建成功不等于接通。必须再读取测试文档，确认标题、来源和正文可见。
- 飞书文档失败时，本地 Obsidian 笔记仍应成功保留，并明确报告失败原因。

## 安装和授权

每次只让用户完成一个需要界面操作的步骤。Agent 负责运行其余命令和检查
结果。

1. 检查 `lark-cli --version`。没有安装时，按官方仓库当前说明运行：
   `npx @larksuite/cli@latest install`。
2. 运行 `lark-cli config init`，让用户在本机交互界面完成一次配置。不要
   要求用户把凭据复制到聊天里。
3. 使用最小业务域发起用户授权：
   `lark-cli auth login --domain docs --domain drive`。
4. 运行 `lark-cli auth status --json --verify`，只有用户身份有效并且权限
   已验证，才继续。

安装命令和参数可能随官方版本更新。若本机 `--help` 与本页不同，以
`lark-cli --help` 和官方仓库为准，不要猜参数。

## 测试写入

先在 Obsidian 创建测试笔记，再用用户身份创建一份飞书文档：

```bash
lark-cli docs +create --api-version v2 --as user \
  --title "赛博三味书屋｜测试笔记" \
  --markdown $'# 赛博三味书屋测试\n\n来源：https://example.com\n\n状态：测试写入'
```

从命令结果取得文档 URL 或 token 后，立即读回：

```bash
lark-cli docs +fetch --api-version v2 --as user --doc "CREATED_DOC_URL_OR_TOKEN"
```

只有读回结果包含测试标题、来源和状态，才运行：

```bash
python3 "<skill-dir>/scripts/setup_state.py" set-destination \
  --destination obsidian-feishu \
  --evidence "CREATED_AND_READ_BACK_TEST_DOC_URL"
```

## 日常写入

1. 先按 [note-schema.md](note-schema.md) 写入并验证 Obsidian 原件。
2. 用相同标题、来源、一句话摘要、核心内容和访问限制创建飞书文档副本。
3. 读回飞书文档，确认主要字段可见。
4. 验收成功后，在本地原件中加入 `feishu_doc` 和 `feishu_doc_url`。
5. 向用户同时返回 Obsidian 文件路径和飞书文档链接。

不要把本地绝对路径、Cookie、授权信息或隐藏配置写进飞书文档。用户没有
要求公开分享时，不修改飞书文档的分享范围。
