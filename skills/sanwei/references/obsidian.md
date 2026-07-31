# Obsidian 仓库设置

## 新建仓库

- 对用户始终称为“赛博三味书屋”。
- macOS 磁盘目录使用 `~/Documents/cyber-sanwei`；Windows 使用
  `%USERPROFILE%\Documents\cyber-sanwei`。不要在注册后改回中文目录名。
- 已有 Obsidian 仓库不受此规则限制；用户选了已有仓库，就保留其原路径。

按这个顺序操作：

1. 运行 `setup_state.py init`，创建英文目录、`.obsidian` 和中文欢迎笔记。
2. 打开 Obsidian 的仓库管理界面。
3. 选择“打开文件夹作为仓库”，选中当前系统对应的上述目录。
4. 再运行 `setup_state.py doctor`。
5. 只有 `registered_in_obsidian` 为 `true`，才打开欢迎笔记并记录
   `vault_registered`。

不要用 `obsidian://open?path=<新目录>` 代替第 2、3 步。Obsidian URI
只能在仓库已经注册后定位文件，未注册时会提示 `Vault not found`。

## 遇到 Vault not found

1. 关闭报错，不要重复点击同一个 URI。
2. 核对 `doctor` 输出中的 `notes_root`。
3. 在 Obsidian 中用“打开文件夹作为仓库”选择该目录。
4. 再次运行 `doctor`，确认 `registered_in_obsidian` 为 `true`。
5. 从 Obsidian 文件列表中打开 `欢迎来到赛博三味书屋.md` 做可见性验收。
