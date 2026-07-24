# 本仓开发闭环

- **版本**：v0.1
- **日期**：2026-07-24
- **用途**：改代码或验环境时的最短路径；对照退出码做决策

---

## 1. 标准回路

```text
拉最新 main → uv sync → 改代码或文档 → 本地命令验证 → format/lint（若改 md）→ 分支提交 → PR
```

代码相关最小验证：

```bash
cd /path/to/lesson-review-ai
uv sync
uv run lesson-review --help
uv run lesson-review check
uv run lesson-review run /path/to/sample.wav --dry-run
```

文档相关：

```bash
npm run format
npm run lint:md
```

---

## 2. 退出码（决策表）

与 [CLI 契约](../01-product/002_cli-contract_CLI命令与运行契约.md) 一致：

| 码  | 含义           | 你该怎么想                          |
| --- | -------------- | ----------------------------------- |
| 0   | 成功           | dry-run 过关或命令完成              |
| 1   | 用户输入问题   | 路径不存在、后缀不支持等；先改输入  |
| 2   | 依赖缺失       | ffmpeg 等 required 项；先装依赖再跑 |
| 3   | 流水线步骤失败 | 转写/LLM 等（后续切片才会常见）     |

`check` / `run --dry-run` 会打印 `[OK]` / `[MISSING]`。  
**required** 缺失 → 通常退出 2；**optional**（如尚未装的 mlx-whisper、未填的 API Key）可先标 MISSING，不阻塞骨架阶段的 dry-run。

---

## 3. 改哪一类东西时先读什么

| 你要改的           | 先读                           |
| ------------------ | ------------------------------ |
| 产品行为 / 验收    | `docs/01-product/`             |
| 技术选型 / 为什么  | `docs/02-architecture/` + ADR  |
| 分支 / PR / Issue  | `docs/03-delivery/`            |
| uv / ffmpeg 不会用 | `docs/90-guides/`（本文档树）  |
| 评价口径 / 提示词  | 上游标准引用 → 再改 `prompts/` |

---

## 4. 协作提醒（避免 vibe 失控）

- 先有契约与 Issue，再让 AI 写代码；合入前看 diff 与退出码，不只看「对话里说成功了」。
- public 仓：不写真名、机构名、品牌名；不提交 `.env` 与真实课例。

---

## 5. 相关文档

- [uv 速查](./001_uv-cheatsheet_uv速查与决策.md)
- [ffmpeg 速查](./002_ffmpeg-basics_抽轨速查.md)
- [DevOps 工作流](../03-delivery/002_devops-workflow_分支PR与门禁.md)
