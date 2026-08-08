# 结构化内容插图

结构图是条件性强制交付物：有真实结构就必须画，没有真实结构就不画。模型不能自行跳过，也不能为凑图伪造关系。

## 什么时候画

每次采集都先让确定性脚本扫描已取得的正文、视频分析和逐字稿：

```bash
<python-command> "<skill-dir>/scripts/visual_gate.py" detect \
  --source "<captured-content-or-analysis>" \
  --source "<transcript-if-any>" \
  --output "<asset-dir>/visual-report.json"
```

用户明确要求画图时追加 `--force-type architecture|flow|decision|relationship|causal|timeline`。报告命中下列任一真实结构时，`required: true`：

- 系统、组件、角色或数据流 → `architecture`；
- 三步以上的 SOP、操作顺序或依赖 → `flow`；
- 分支、判断条件、适用/不适用 → `decision`；
- 分层模型、核心观点与多个下游要素 → `relationship`；
- 明确的原因、结果和传导 → `causal`；
- 演进阶段、里程碑或完整叙事弧 → `timeline`。

只有 1-2 步、普通列表、简单摘要、证据不足或节点之间没有真实关系时，不画。

## 三种模式的上限

- `同步笔记`：原文确实有流程或框架时，最多 1 张。
- `蒸馏笔记`：流程、框架、分支或短片节奏清晰时，1-3 张。
- `详细拆解`：完整使用前两种模式中最有信息量的图，通常 1-3 张，不重复画同一关系。

## 图形怎么选

- `architecture`：系统、角色、组件和数据流。
- `flow`：SOP、生产流程、前后依赖。
- `decision`：决策树、多路径、适用/不适用条件。
- `relationship`：分层、中心观点与多个组成部分或影响。
- `causal`：原因、传导和结果。
- `timeline`：短片节奏、叙事弧线、时间阶段。

## 生成方式

1. 根据报告中的证据片段生成 Mermaid `flowchart`。节点限定 2–8 个，标题用短语；关系只能来自来源证据，分析推断必须在节点中标明。
2. 用固定版本渲染器先做几何检查，再生成 PNG：

```bash
npx -y @larksuite/whiteboard-cli@^0.2.13 \
  -i "<asset-dir>/diagram.mmd" --check > "<asset-dir>/diagram-check.json"
npx -y @larksuite/whiteboard-cli@^0.2.13 \
  -i "<asset-dir>/diagram.mmd" -o "<asset-dir>/diagram.png"
```

检查命令非零退出、文字溢出、节点重叠或文字遮挡任一不为零时，必须修改同一份 Mermaid 后重跑。

3. 让当前支持图片输入的模型查看 `diagram.png`，对照来源证据生成下面的 `diagram-review.json`。没有图片能力时停止并明确报告 `visual_review_unavailable`，不能把文本模型自检写成通过。

```json
{
  "status": "pass",
  "text_readable": true,
  "no_overlap": true,
  "no_cropping": true,
  "evidence_alignment": true,
  "relationship_errors": []
}
```

4. 完成门禁：

```bash
<python-command> "<skill-dir>/scripts/visual_gate.py" finalize \
  --report "<asset-dir>/visual-report.json" --artifact-root "<asset-dir>" \
  --source "<asset-dir>/diagram.mmd" --preview "<asset-dir>/diagram.png" \
  --check "<asset-dir>/diagram-check.json" --review "<asset-dir>/diagram-review.json"
```

5. 将 PNG 嵌入最相近的固定栏目，并把同一路径写进 YAML `visual_assets`：

```markdown
![SOP 流程图](../_assets/<capture-id>/diagram.png)
```

6. 图后用 2–5 句文字复述关键关系，保证搜索和屏幕阅读器仍能理解；在 Obsidian 中回看后才能完成。

示例见 [examples/structured-sop.json](../examples/structured-sop.json)。

## 证据与发布边界

- 节点、顺序和分支必须来自已取得的内容。模型推导的关系要标注“分析推断”。
- 图不能替代逐字稿、原文证据或镜头时码。
- 不在 HTML 中放远程脚本、跟踪代码、Cookie 或外部资源。
- 发布到飞书文档时上传已通过门禁的 PNG，并在最终读回中检查图片和图注。无法读回时不声称图已发布。
