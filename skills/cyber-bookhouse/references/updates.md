# 自更新

当用户说“更新赛博书屋”“检查最新版”或类似表达时，使用包内更新器，不让用户重新
下载 ZIP。第一次 onboarding 时也检查一次；普通采集任务不因网络检查失败而中断。

## 检查最新版

先解析 `SKILL_DIR`，再运行：

```bash
<python-command> "<skill-dir>/scripts/update_skill.py" --check
```

更新器只访问 GitHub 官方 API 和 Release 附件，比较 `release.json` 中的版本与 build。
同一版本被修订时，build 增加，因此也能识别并更新。

如果结果为 `update_available: false`，报告当前已是最新版。如果 GitHub 暂时不可访问，
如实报告检查失败；不要因此阻止用户继续使用已有 Skill。

## 执行更新

发现新版后，先告诉用户当前版本、最新版本以及会备份旧版，询问是否立即更新。只有
用户明确同意后，才运行：

```bash
<python-command> "<skill-dir>/scripts/update_skill.py" --apply --target auto
```

`--apply` 会依次完成：

1. 获取 GitHub Latest Release 元数据；
2. 下载 `cyber-bookhouse.zip`；
3. 按 GitHub 返回的 SHA-256 校验附件；
4. 拒绝路径穿越、符号链接、错误根目录或版本不一致的压缩包；
5. 调用新版安装器，备份旧目录并原位安装；
6. 回读安装结果。

Codex 与 Claude Code 可自动识别当前安装目标。若 Skill 不在标准用户级目录，明确指定
`--target codex`、`--target claude` 或 `--target both`。更新完成后，不继续依赖当前任务
已经载入的旧说明；让用户新开任务或重启 Agent，再调用一次 `cyber-bookhouse`。

WorkBuddy 当前没有稳定的开放接口允许 Skill 安全覆盖自己的安装目录。更新器可以检查
最新版，但 WorkBuddy 的覆盖仍须在“技能”界面重新上传最新版 ZIP；不要声称已自动覆盖。

## 安全边界

- 不静默升级，不把检查结果当作更新授权。
- 不接受任意下载地址，只使用固定 GitHub 仓库的 Latest Release。
- 不跳过 GitHub 附件摘要校验。
- 不删除备份；备份位置由安装器返回。
- 不在更新过程中修改其他 Skills。
