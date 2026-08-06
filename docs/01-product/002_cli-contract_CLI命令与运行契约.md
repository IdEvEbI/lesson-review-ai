# CLI 命令与运行契约

- **版本**：v1.2.1
- **日期**：2026-08-06
- **状态**：目标契约（实现按本文落地；偏差须更新本文）

---

## 1. 设计原则

- **单条命令应能完成 MVP 竖切所需的端到端流水线**，以减少维护者记忆负担。
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

| 参数 / 选项       | 说明                                                                                                                                            |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `<路径>`          | 单个视频或音频文件                                                                                                                              |
| `--output-dir`    | 默认 `./output`                                                                                                                                 |
| `--language`      | 默认 `zh`（转写语言提示）                                                                                                                       |
| `--whisper-model` | 默认 `mlx-community/whisper-large-v3-turbo`                                                                                                     |
| `--llm-model`     | 默认读环境变量（如 `deepseek-v4-flash`）                                                                                                        |
| `--lesson-type`   | 可选：`principle` \| `code` \| `lab`；非法值（如 `lib`）**报错退出**，不静默回落；省略则按文件名推断（见报告契约 §10.1；安装/环境类默认 `lab`） |
| `--dry-run`       | 只校验依赖与输入，不调用模型                                                                                                                    |
| `--skip-llm`      | 流水线仅执行至转写步骤，写出 `transcript_raw.json` 与 manifest，不调用 LLM                                                                      |
| `--force`         | 覆盖已有同 `run_id` 碰撞的输出目录（极少见；同秒同文件）                                                                                        |

完整 `run`（无 `--skip-llm`）要求 `LLM_API_KEY`；`--dry-run` 仍可将 Key 标为 optional，但会提示全量运行需要 Key。

输出目录为 `output/<run_id>/`，其中 `run_id = YYYYMMDD-HHMMSS_<sha256前8位>`。

### 2.2 `run --module`（模块批处理）

| 参数 / 选项   | 说明                                                                         |
| ------------- | ---------------------------------------------------------------------------- |
| 多个 `<路径>` | 3～5 个文件；少于 3 或多于 5 时 **警告**仍可运行，风险与结果由维护者自行承担 |
| 排序          | 按文件名前缀数字升序；解析失败则警告并按字典序                               |

模块模式在单视频流水线之上增加：**模块层结构合并**与**跨视频嵌套检查**（见报告契约）。

### 2.3 分步子命令（调试，M1 起逐步提供）

```bash
lesson-review extract-audio <视频> [-o <音频>] [--format mp3|wav] [--output-dir ./output]
lesson-review transcribe <音频> [-o <transcript.json>] [--language zh] [--whisper-model <id>] [--output-dir ./output]
lesson-review correct <transcript> [-o <corrected.md>] [--llm-model <id>] [--output-dir ./output]
lesson-review batch-conduct <目录> [--limit N] [--with-outline] [--output-dir ./output] [--force]
lesson-review analyze <corrected> --mode single|module ...
```

| 子命令 / 选项     | 说明                                                                                               |
| ----------------- | -------------------------------------------------------------------------------------------------- |
| `extract-audio`   | 仅抽轨 / 规范化音频；不调用 LLM                                                                    |
| `--format`        | 默认 `mp3`（16 kHz 单声道约 96 kbps）；`wav` 为 16 kHz 单声道 PCM                                  |
| `-o` / `--output` | 显式输出路径；省略时按子命令默认布局                                                               |
| `--output-dir`    | 省略 `-o` 时的输出根目录，默认 `./output`                                                          |
| `transcribe`      | 本地 mlx-whisper 转写；写出 `transcript_raw.json`（含片段时间戳）                                  |
| `--language`      | 默认读 `WHISPER_LANGUAGE`，否则 `zh`                                                               |
| `--whisper-model` | 默认读 `WHISPER_MODEL`，否则 `mlx-community/whisper-large-v3-turbo`                                |
| `correct`         | LLM 纠错（补标点、降噪）；写出 `transcript_corrected.md`                                           |
| `batch-conduct`   | 目录批处理：抽轨 → 转写 → 纠错 → 言行扫描；写出 `output/<输入目录名>/summary.md`（见下表增强字段） |
| `--with-outline`  | （规划）各段追加讲解结构提纲进 `summary`；默认关闭以控制 LLM 成本                                  |
| `--force`         | 覆盖已存在的同名批产出目录                                                                         |
| `--llm-model`     | 默认读 `LLM_MODEL`，否则 `deepseek-v4-flash`                                                       |

#### `batch-conduct` 汇总字段（`summary.md` / manifest）

| 字段 / 区块            | 说明                                                                                                                           |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| 产出目录名             | 与输入目录 basename 同名；无效名时回退 `conduct_YYYYMMDD-HHMMSS`                                                               |
| 视频时长               | 优先 `ffprobe`；否则用 ASR `segments` 末时间；总览表与批合计                                                                   |
| `pedagogy_type`        | 旁路细课型：上游备课 `004`～`010` 之一，或 `other`（待维护者校准）；**不等于**主路径 `lesson_type`（`principle`/`code`/`lab`） |
| `pedagogy_type_source` | `llm` \| `override` \| `other`                                                                                                 |
| 日分布                 | 按**时长加权**统计各 `pedagogy_type` 占比（投诉日「开场/吹牛 vs 代码」用）                                                     |
| 讲解结构（可选）       | `--with-outline` 时：每段 5～12 个节点摘要；宜带时间锚；**不**跑 Pass A / coach                                                |
| 言行扫描               | 既有三类 + 处置路径；与时长 / 课型独立                                                                                         |

细课型枚举（旁路；文案对齐上游备课方法专文，公开文档不写品牌）：

| 代码    | 对齐上游（备课方法） | 摘要用途（批扫）       |
| ------- | -------------------- | ---------------------- |
| `004`   | 阶段第一课怎么讲     | 开场 / 阶段导入向      |
| `005`   | 简介类               | 概念铺垫向             |
| `006`   | 实操类               | 安装配置 / 跟做向      |
| `007`   | 代码语法类           | 语法与 API 向          |
| `008`   | 案例类               | 综合案例向             |
| `009`   | 原理类               | 机制讲解向             |
| `010`   | 项目类               | 项目推进向             |
| `other` | —                    | 模型不确定；待人工校准 |

判不出或置信不足时必须标 `other`，**禁止**为凑分布硬猜。维护者可在产物中覆盖后重渲 summary（实现见对应 Issue）。

子命令与 `run` 共用同一套配置与退出码约定；`extract-audio` / `transcribe` 不要求 `LLM_API_KEY`。`correct` **要求** `LLM_API_KEY`。`transcribe` 需要可导入的 `mlx-whisper` 与 PATH 上的 `ffmpeg`。

`transcribe` 省略 `-o` 时默认写出：`<output-dir>/<stem>/transcript_raw.json`。  
`correct` 省略 `-o` 时默认写出：`<output-dir>/<stem>/transcript_corrected.md`（若输入为 `…/<stem>/transcript_raw.json`，则 stem 取父目录名）。

五类提示词位于仓库根目录 `prompts/`；`run` 全量路径使用 `system_tone` + `asr_correct` / `structure_single` / `coach_feedback`。`structure_module` 供模块批处理模式使用（对应 E5）。`batch-conduct` 另用 `conduct_scan`（言行扫描）；旁路增强另用细课型 / 可选结构专用提示词（实现随 Issue 落地，不挤占主路径 `lesson_type`）。

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
    teaching_outline.md    # 讲解重点提纲（回避 Pass A issue）
    coach.md               # 发给老师的短稿（结论 / Top3 / 四维）
    suggestions.md         # 合格线/水平线 + 待回放（仅进 report）
    report.md              # 最终报告（结构见报告契约）
    logs/                  # 预留
```

`run_id`：`YYYYMMDD-HHMMSS_<输入文件 SHA256 前 8 位>`，便于并排对比多次迭代。

全量 `run` 在纠错之后为 **Pass A → 结构 → 讲解提纲 → Pass B（coach/report）**。字段见 [报告契约](./003_report-contract_报告结构与验收.md)（当前 **v0.7.5 草案**；v0.7.2 起 lab 路径已落地）、[ADR-0004](../02-architecture/adr/0004_two-pass-knowledge-review.md)、[ADR-0005](../02-architecture/adr/0005_clarity-and-playback-boundary.md)、[ADR-0006](../02-architecture/adr/0006_lab-pedagogy-checks.md)。

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
| `lesson_type`                | `principle` \| `code` \| `lab`                           |
| `lesson_type_source`         | `cli` \| `inferred`                                      |
| `report_path`                | 最终报告相对路径                                         |

manifest 用于可复现与提示词回归，**不含** API Key 与逐字稿全文。

---

## 7. 修订记录

| 版本   | 日期       | 说明                                                             |
| ------ | ---------- | ---------------------------------------------------------------- |
| v0.1   | 2026-07-23 | 首版契约                                                         |
| v0.2   | 2026-07-24 | `extract-audio`：默认 mp3、`--format`、默认输出路径              |
| v0.3   | 2026-07-24 | `transcribe`：mlx-whisper、`transcript_raw.json`、模型/语言参数  |
| v0.4   | 2026-07-25 | `correct`：prompts 骨架、DeepSeek 兼容客户端、纠错输出路径       |
| v0.5   | 2026-07-25 | `run` 单视频竖切：`run_id` 目录、manifest、report.md             |
| v0.6   | 2026-07-25 | 约定 Pass A `knowledge_review.json`（实现待 ADR-0004 确认）      |
| v0.7   | 2026-07-25 | 对齐报告契约 v0.3：`clarity`、coach/report 待回放；关联 ADR-0005 |
| v0.8   | 2026-07-25 | 对齐报告契约 v0.4：coach 仅 V1–V4；提纲 / lesson_type 列入下一批 |
| v0.9   | 2026-07-25 | `teaching_outline.md`、`--lesson-type`、manifest 课型字段        |
| v1.0   | 2026-07-25 | `coach.md` 短稿 + `suggestions.md`；对齐报告契约 v0.6            |
| v1.1   | 2026-07-25 | 对齐报告契约 v0.7：lab L1/L2/L3、安装类默认 lab；关联 ADR-0006   |
| v1.1.1 | 2026-07-25 | 对齐报告契约 v0.7.1：L2/L3 课型无关措辞；确认前仍不改实现        |
| v1.1.2 | 2026-07-25 | `--lesson-type` 非法值报错；对齐报告契约 v0.7.2 推荐讲解路径     |
| v1.2   | 2026-07-29 | 新增 `batch-conduct`：目录排序转写/纠错 + 脏话与贬低前任扫描     |
| v1.2.1 | 2026-08-06 | 可读性润色；报告契约版本指针改为 v0.7.5 草案                     |
| v1.2.2 | 2026-08-06 | `batch-conduct` 产出目录改为与输入目录同名                       |
| v1.3   | 2026-08-06 | `batch-conduct`：时长、细课型占比、可选结构提纲（旁路增强）      |
