# Issue 草案 · 边打字边讲停顿误伤防护

- **建议标题**：`feat(review): reduce false positives from typing-while-teaching pauses`
- **类型**：`docs` + `feat(prompts)`（可选后续启发式）
- **优先级**：投诉 / 课评共用；建议先于声学旁路落地
- **状态**：本地草案（待维护者授权后创建 GitHub Issue）

---

## Background

教师常在**共屏跟敲**时边打字边讲解。纠错逐字稿会显得断续；若教练据此写「磕巴 / 不流畅」，易误伤实际在操作演示的教师。

已有闸门：报告契约表达噪声；ADR-0005；`coach_feedback` 相关约束。需要写成可验收的政策，并视需要加轻量启发式。

产品同步（2026-08）：声学旁路 / 打字停顿误伤 / 单视频多交付点。

## Goal

Pass B / 结构建议**不得**把操作间隙当成表达不合格，除非有摘句证明**损害理解或合格线**。

## In scope

- [ ] 报告契约（及 ADR-0005 补丁或短 ADR）写清：
  - 评判「学员是否跟得上交付」，不是「逐字稿是否连贯」
  - 长停顿 + lab/code/共屏跟敲语境 → 默认「操作间隙 / 跟敲节奏」（水平线或不写）
  - ASR 纠错**不得**为流畅而抹平停顿（保留证据）
- [ ] 更新 `coach_feedback` / `structure_single` / `system_tone` 反模式说明
- [ ] 可选弱启发式（可同 PR 或后续）：`transcript_raw.json` 时间戳空隙 → `pause_spans` 提示传入 Pass B（仅上下文，不直接变 issue）
- [ ] 维护者试用清单增加对应勾选项

## Out of scope

- MVP 阶段强制上线键盘声 ML 分类器
- 自动删改逐字稿停顿
- 把打字慢写成合格线问题

## Acceptance

- [ ] lab/code 样例含明显打字停顿时，Top3 **不以**「表达磕巴」打头，除非另有 clarity/accuracy 摘句证据
- [ ] 契约与 prompts 用完整句子写清边界
- [ ] 可选：`90-guides` 或交付清单中有一条回归注意

## Depends on

无硬阻塞；可先只合文档 + prompts，再补 pause 启发式。
