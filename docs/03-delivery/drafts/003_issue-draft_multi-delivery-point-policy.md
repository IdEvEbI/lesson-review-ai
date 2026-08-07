# Issue 草案 · 单视频多交付点政策（主交付优先）

- **建议标题**：`docs+product: multi-delivery-point policy for long single videos`
- **类型**：`docs`（契约 / PRD / 指南）+ prompts；CLI 锚点为可选后续
- **优先级**：并入 **E4c-2**（见 [004 单视频教练强化](./004_issue-draft_single-video-coach-course-design.md)）；不再作为独立主线抢排期
- **状态**：本地草案（随 E4c 开 Issue 时吸收验收项）

---

## Background

现场（尤其大模型学科）常见**一条长录像含多个交付点**。若按「一视频必须完美总分总嵌套」严判，易打消尚可授课教师的积极性；若过松，又只剩「再流畅一点」类空话。

产品同步（2026-08）：声学旁路 / 打字停顿误伤 / 单视频多交付点。

## Goal

先冻结**维护者可读的政策**；需要时再加轻量 CLI / 报告支持。

## In scope（文档 / 契约优先）

- [ ] 更新报告契约与 PRD 说明：
  - 单次 `run` 合格线优先盯**主交付 1～2 个点**是否讲清、可跟做
  - 标题过泛 → `anchor_strength=weak`，更多 `unverified` / 待回放
  - 次要话题 → 水平线或待核实，不自动必改
  - 投诉深挖：先切片段或给出具体锚点，再跑单视频课评
- [ ] prompts：Pass A / structure / coach 遵守「主交付优先」
- [ ] 指南：扩展 `005` 或短文，说明投诉场景如何选锚点
- [ ] 平衡规则写死：过严 = 百科清单 / 完美嵌套；过松 = 只谈流畅；中间 = 有摘句的主交付讲不清 / 硬伤 / 言行

## Out of scope（本 Issue）

- 全自动主题切分 / 镜头分割模型
- 将 `lesson_type` 扩成上游六课型枚举（仍用 §7.1 映射）
- 替代模块模式 E5

## Optional follow-up（点名但不阻塞）

- CLI `--title-anchor` / `--focus` 注入 Pass A
- `structure.md` 给出软性分段建议但不因此失败整次 run

## Acceptance

- [ ] 维护者可一次读完契约增补
- [ ] 脱敏多话题样例：合格线不被次要嵌套缺口刷屏
- [ ] 投诉操作顺序写清：`batch-conduct` → 点选 1～2 段 → 带具体锚点的单视频 `run`

## Suggested order

契约 / PRD / 指南 → prompts →（可选）CLI 锚点参数。
