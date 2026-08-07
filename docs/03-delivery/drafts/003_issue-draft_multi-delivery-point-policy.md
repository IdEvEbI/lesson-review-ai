# Issue 草案 · 单视频多交付点政策（主交付优先）

- **建议标题**：`docs+product: multi-delivery-point policy for long single videos`
- **类型**：`docs`（契约 / PRD / 指南）+ prompts；CLI 锚点为可选后续
- **优先级**：并入 **E4c-2**（见 [004 单视频教练强化](./004_issue-draft_single-video-coach-course-design.md)）；不再作为独立主线抢排期
- **状态**：**已并入 E4c-2**（报告契约 v0.8.0、prompts、指南 `005` §5；Issue [#39](https://github.com/IdEvEbI/lesson-review-ai/issues/39)）

---

## Background

现场（尤其大模型学科）常见**一条长录像含多个交付点**。若按「一视频必须完美总分总嵌套」严判，易打消尚可授课教师的积极性；若过松，又只剩「再流畅一点」类空话。

## Goal

先冻结**维护者可读的政策**；需要时再加轻量 CLI / 报告支持。

## In scope（文档 / 契约优先）

- [x] 更新报告契约：主交付 1～2 点；弱锚点更保守；次要话题不刷合格线；投诉先切段
- [x] prompts：Pass A / structure / coach / outline 遵守「主交付优先」与反硬套总分总
- [x] 指南：`005` §5 投诉选锚与主交付读法
- [x] 平衡规则写死：过严 / 过松 / 中间（契约 §1.16）

## Out of scope（本 Issue）

- 全自动主题切分 / 镜头分割模型
- 将 `lesson_type` 扩成上游六课型枚举（仍用 §7.1 映射）
- 替代模块模式 E5

## Optional follow-up（点名但不阻塞）

- CLI `--title-anchor` / `--focus` 注入 Pass A
- 金样例上验证「合格线不被次要嵌套刷屏」（E4c-5）

## Acceptance

- [x] 维护者可一次读完契约增补
- [ ] 脱敏多话题样例：合格线不被次要嵌套缺口刷屏（E4c-5）
- [x] 投诉操作顺序写清：`batch-conduct` → 点选 1～2 段 → 带具体锚点的单视频 `run`
