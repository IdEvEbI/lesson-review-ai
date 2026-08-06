# Issue 草案 · 声学能量旁路（投诉时间轴线索）

- **建议标题**：`feat(audio): acoustic energy bypass for complaint timeline cues`
- **类型**：`feat` + ADR
- **优先级**：投诉核查增强（O4 合入后；不阻塞主课评路径）
- **状态**：本地草案（待维护者授权后创建 GitHub Issue）

---

## Background

投诉核查有时需要一张**音量 / 停顿 / 能量起伏时间轴**，帮助维护者快速定位疑似灌水高能段或异常长静音。该信号**不得**升格为情绪打分或合格线门禁。

产品同步（2026-08）：声学旁路 / 打字停顿误伤 / 单视频多交付点。

## Goal

可选**旁路**：给定音频（或视频抽轨），写出可机读能量时间轴 + 短 Markdown 摘要，供人工回放。

## In scope

- [ ] ADR：声学特征仅为**待核实 / 投诉回放线索**，不得单独进入 Top3 / 合格线
- [ ] MVP 特征：窗级能量 / RMS；可选低能量静音段检测
- [ ] CLI 旁路（建议）：如 `lesson-review audio-energy <audio|video>` → `output/` 下 `energy.json` + `energy_summary.md`
- [ ] 时间戳可对齐播放器跳转
- [ ] `docs/90-guides/` 短说明（仅投诉场景；文档不写真名 / 品牌）

## Out of scope

- 情绪分类标签（愤怒 / 高兴等）作为产品真相
- 仅凭能量自动判定「吹牛灌水」或考勤迟到早退
- 人脸 / 姿态多模态
- 将能量分数并入 Pass A / coach Top3

## Acceptance

- [ ] 脱敏样例上，维护者能从摘要列出 3～5 个「建议回放区间」
- [ ] 文档写明：非合格线；打字静音、学员练习、增益差异会导致假阳性
- [ ] 合成短 wav 的聚合单测；真实课例媒体不入库

## Suggested order

ADR / 契约一句 → 库 + CLI → 指南。可不改主路径 `run`。
