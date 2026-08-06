# 单视频课评跑通说明（KR4.1）

- **版本**：v0.1
- **日期**：2026-08-06
- **用途**：按步骤复现「抽轨 → 转写 → 纠错 → Pass A → 结构 → 提纲 → 教练报告」单视频端到端
- **产品源**：[PRD](../01-product/001_prd_课评教练MVP产品说明.md)、[CLI 契约](../01-product/002_cli-contract_CLI命令与运行契约.md)、[报告契约](../01-product/003_report-contract_报告结构与验收.md)
- **前置**：已完成 [开发环境与 uv](../03-delivery/003_dev-environment_开发环境与uv.md)；本地 `.env` 含 `LLM_API_KEY`；手头有一份**脱敏**样例媒体（不入库）

---

## 1. 学习目标

读完并按本文操作后，应当能够：

1. 在本机对单个视频跑通 `lesson-review run`；
2. 指出 `output/<run_id>/` 下关键产物与阅读顺序；
3. 用退出码区分输入错误、依赖缺失与流水线失败。

---

## 2. 一次完整运行

将路径替换为本地脱敏样例（示例仅示意）：

```bash
cd /path/to/lesson-review-ai
uv sync
uv run lesson-review check
uv run lesson-review run "data/input/<脱敏样例>.mp4" --lesson-type principle
```

可选：

| 选项            | 说明                                               |
| --------------- | -------------------------------------------------- |
| `--lesson-type` | `principle` \| `code` \| `lab`；非法值会报错退出   |
| `--dry-run`     | 只校验依赖与输入，不调用模型                       |
| `--skip-llm`    | 只做到转写，写出 `transcript_raw.json` 与 manifest |
| `--output-dir`  | 默认 `./output`                                    |

实操安装类样例建议显式传 `--lesson-type lab`，或依赖文件名启发式（见报告契约 §10.1）。

---

## 3. 预期产物与阅读顺序

成功后终端会打印 `run_id` 与报告路径。目录大致为：

```text
output/<run_id>/
  manifest.json
  transcript_raw.json
  transcript_corrected.md
  knowledge_review.json
  structure.md
  teaching_outline.md
  coach.md
  suggestions.md
  report.md
```

建议阅读顺序：

1. **`report.md`**：完整课评（含专业预审渲染、结构、建议）。
2. **`coach.md`**：可发给老师的短稿（结论 / Top3 / V1–V4）。
3. **`suggestions.md`**：合格线 / 水平线 / 待回放（仅进报告）。
4. **`manifest.json`**：模型、课型来源、可复现元数据。

---

## 4. 退出码（摘要）

| 码  | 含义                                     |
| --- | ---------------------------------------- |
| 0   | 成功                                     |
| 1   | 用户输入错误（文件不存在、格式不支持等） |
| 2   | 依赖缺失（ffmpeg、模型、无 API Key 等）  |
| 3   | 流水线步骤失败（转写或 LLM 调用失败等）  |

完整约定见 CLI 契约 §4。

---

## 5. 常见失败与处理

| 现象                     | 处理方向                                          |
| ------------------------ | ------------------------------------------------- |
| `check` 报缺 ffmpeg      | `brew install ffmpeg`；确认 PATH                  |
| `LLM_API_KEY` missing    | 按 `.env.example` 配置本地 `.env`（勿提交）       |
| 首次转写很慢             | mlx-whisper 下载模型；等待缓存完成                |
| `--lesson-type lib` 报错 | 仅允许 principle / code / lab                     |
| 报告建议空泛或课型不对   | 指定 `--lesson-type`；对照 prompts 与报告契约回归 |

分步调试可用：`extract-audio` → `transcribe` → `correct`（见 CLI 契约与 [003 开发闭环](./003_cli-dev-loop_本仓开发闭环.md)）。

---

## 6. 相关文档

- [003 本仓开发闭环](./003_cli-dev-loop_本仓开发闭环.md)（日常短回路与 dry-run）
- [004 言行扫描](./004_batch-conduct_言行扫描速查.md)（旁路，非本路径）
- [上游标准引用](../02-architecture/003_upstream-standards_上游标准引用.md)
