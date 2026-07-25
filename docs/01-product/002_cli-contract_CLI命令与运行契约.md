# CLI 命令与运行契约

- **版本**：v0.8
- **日期**：2026-07-25
- **状态**：目标契约（实现按本文落地；偏差须更新本文）

---

## 1. 设计原则

- **一条命令跑通竖切**：减少维护者记忆负担。
- **可组合**：允许分步调试（只抽轨、只转写等），便于 Issue 分期实现。
- **可观测**：每步写日志；整次运行写 `manifest.json`。
- **机器可读**：为后续 CI / 脚本预留 `--json` 状态输出（可在 M2 实现）。

---

## 2. 命令入口（目标）

```bash
lesson-review run <路径> [选项]
lesson-review run --module <路径1> <路径2> ... [选项]
```

安装后通过 `uv run lesson-review` 或等价虚拟环境调用；包名与入口在仓库骨架 Issue 中确定。

### 2.1 `run`（单文件）

| 参数 / 选项       | 说明                                                          |
| ----------------- | ------------------------------------------------------------- |
| `<路径>`          | 单个视频或音频文件                                            |
| `--output-dir`    | 默认 `./output`                                               |
| `--language`      | 默认 `zh`（转写语言提示）                                     |
| `--whisper-model` | 默认 `mlx-community/whisper-large-v3-turbo`                   |
| `--llm-model`     | 默认读环境变量（如 `deepseek-v4-flash`）                      |
| `--dry-run`       | 只校验依赖与输入，不调用模型                                  |
| `--skip-llm`      | 只做到转写（写出 `transcript_raw.json` + manifest，不调 LLM） |
| `--force`         | 覆盖已有同 `run_id` 碰撞的输出目录（极少见；同秒同文件）      |

完整 `run`（无 `--skip-llm`）要求 `LLM_API_KEY`；`--dry-run` 仍可将 Key 标为 optional，但会提示全量运行需要 Key。

输出目录为 `output/<run_id>/`，其中 `run_id = YYYYMMDD-HHMMSS_<sha256前8位>`。

### 2.2 `run --module`（模块批处理）

| 参数 / 选项   | 说明                                                      |
| ------------- | --------------------------------------------------------- |
| 多个 `<路径>` | 3～5 个文件；少于 3 或多于 5 **警告**仍可跑（维护者自负） |
| 排序          | 按文件名前缀数字升序；解析失败则警告并按字典序            |

模块模式在单视频流水线之上增加：**模块层结构合并**与**跨视频嵌套检查**（见报告契约）。

### 2.3 分步子命令（调试，M1 起逐步提供）

```bash
lesson-review extract-audio <视频> [-o <音频>] [--format mp3|wav] [--output-dir ./output]
lesson-review transcribe <音频> [-o <transcript.json>] [--language zh] [--whisper-model <id>] [--output-dir ./output]
lesson-review correct <transcript> [-o <corrected.md>] [--llm-model <id>] [--output-dir ./output]
lesson-review analyze <corrected> --mode single|module ...
```

| 子命令 / 选项     | 说明                                                                |
| ----------------- | ------------------------------------------------------------------- |
| `extract-audio`   | 仅抽轨 / 规范化音频；不调用 LLM                                     |
| `--format`        | 默认 `mp3`（16 kHz 单声道约 96 kbps）；`wav` 为 16 kHz 单声道 PCM   |
| `-o` / `--output` | 显式输出路径；省略时按子命令默认布局                                |
| `--output-dir`    | 省略 `-o` 时的输出根目录，默认 `./output`                           |
| `transcribe`      | 本地 mlx-whisper 转写；写出 `transcript_raw.json`（含片段时间戳）   |
| `--language`      | 默认读 `WHISPER_LANGUAGE`，否则 `zh`                                |
| `--whisper-model` | 默认读 `WHISPER_MODEL`，否则 `mlx-community/whisper-large-v3-turbo` |
| `correct`         | LLM 纠错（补标点、降噪）；写出 `transcript_corrected.md`            |
| `--llm-model`     | 默认读 `LLM_MODEL`，否则 `deepseek-v4-flash`                        |

子命令与 `run` 共用同一套配置与退出码约定；`extract-audio` / `transcribe` 不要求 `LLM_API_KEY`。`correct` **要求** `LLM_API_KEY`。`transcribe` 需要可导入的 `mlx-whisper` 与 PATH 上的 `ffmpeg`。

`transcribe` 省略 `-o` 时默认写出：`<output-dir>/<stem>/transcript_raw.json`。  
`correct` 省略 `-o` 时默认写出：`<output-dir>/<stem>/transcript_corrected.md`（若输入为 `…/<stem>/transcript_raw.json`，则 stem 取父目录名）。

五类提示词位于仓库根目录 `prompts/`；`run` 全量路径使用 `system_tone` + `asr_correct` / `structure_single` / `coach_feedback`。`structure_module` 留给模块模式（E5）。

---

## 3. 配置优先级

1. 命令行参数
2. 环境变量（见仓库 `.env.example`）
3. 默认值（文档与代码一致）

---

## 4. 退出码（约定）

| 码  | 含义                                       |
| --- | ------------------------------------------ |
| 0   | 成功                                       |
| 1   | 用户输入错误（文件不存在、格式不支持）     |
| 2   | 依赖缺失（ffmpeg、模型未下载、无 API Key） |
| 3   | 流水线步骤失败（转写 / LLM 调用失败）      |

---

## 5. 运行目录布局（单次 run）

```text
output/
  <run_id>/
    manifest.json
    audio/                 # 视频抽轨或音频副本
    transcript_raw.json
    transcript_corrected.md
    knowledge_review.json  # Pass A 专业预审（含 accuracy/clarity/case/coverage_gap）
    structure.md           # 结构要点（Markdown）
    coach.md               # Pass B 综合建议（中间稿；含待回放确认）
    report.md              # 最终报告（结构见报告契约）
    logs/                  # 预留
```

`run_id`：`YYYYMMDD-HHMMSS_<输入文件 SHA256 前 8 位>`，便于并排对比多次迭代。

全量 `run` 在纠错之后为 **Pass A（专业预审）→ Pass B（结构/建议/成稿）**。字段、闸门、Top3 权重与「待回放确认」见 [报告契约](./003_report-contract_报告结构与验收.md)（**v0.4 已确认**）、[ADR-0004](../02-architecture/adr/0004_two-pass-knowledge-review.md)、[ADR-0005](../02-architecture/adr/0005_clarity-and-playback-boundary.md)。讲解重点提纲与 `lesson_type` 见报告契约 §9（下一批提交）。

---

## 6. manifest.json（最小字段）

| 字段                         | 说明                                                     |
| ---------------------------- | -------------------------------------------------------- |
| `run_id`                     | 本次运行 ID                                              |
| `mode`                       | `single` \| `module`                                     |
| `inputs`                     | 文件路径列表 + 内容哈希（SHA256 前 8 位）                |
| `started_at` / `finished_at` | ISO8601                                                  |
| `asr`                        | 引擎、模型 id                                            |
| `llm`                        | provider、model、prompt 文件版本（git 短 hash 或版本号） |
| `steps`                      | 各步状态与耗时                                           |
| `report_path`                | 最终报告相对路径                                         |

manifest 用于可复现与提示词回归，**不含** API Key 与逐字稿全文。

---

## 7. 修订记录

| 版本 | 日期       | 说明                                                             |
| ---- | ---------- | ---------------------------------------------------------------- |
| v0.1 | 2026-07-23 | 首版契约                                                         |
| v0.2 | 2026-07-24 | `extract-audio`：默认 mp3、`--format`、默认输出路径              |
| v0.3 | 2026-07-24 | `transcribe`：mlx-whisper、`transcript_raw.json`、模型/语言参数  |
| v0.4 | 2026-07-25 | `correct`：prompts 骨架、DeepSeek 兼容客户端、纠错输出路径       |
| v0.5 | 2026-07-25 | `run` 单视频竖切：`run_id` 目录、manifest、report.md             |
| v0.6 | 2026-07-25 | 约定 Pass A `knowledge_review.json`（实现待 ADR-0004 确认）      |
| v0.7 | 2026-07-25 | 对齐报告契约 v0.3：`clarity`、coach/report 待回放；关联 ADR-0005 |
| v0.8 | 2026-07-25 | 对齐报告契约 v0.4：coach 仅 V1–V4；提纲 / lesson_type 列入下一批 |
