# CLI 命令与运行契约

- **版本**：v0.1
- **日期**：2026-07-23
- **状态**：目标契约（实现前约定；首个 CLI Issue 按本文落地，偏差须更新本文）

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

| 参数 / 选项       | 说明                                        |
| ----------------- | ------------------------------------------- |
| `<路径>`          | 单个视频或音频文件                          |
| `--output-dir`    | 默认 `./output`                             |
| `--language`      | 默认 `zh`（转写语言提示）                   |
| `--whisper-model` | 默认 `mlx-community/whisper-large-v3-turbo` |
| `--llm-model`     | 默认读环境变量（如 `deepseek-v4-flash`）    |
| `--dry-run`       | 只校验依赖与输入，不调用模型                |
| `--skip-llm`      | 只做到转写（调试用）                        |
| `--force`         | 覆盖已有同 run 输出目录                     |

### 2.2 `run --module`（模块批处理）

| 参数 / 选项   | 说明                                                      |
| ------------- | --------------------------------------------------------- |
| 多个 `<路径>` | 3～5 个文件；少于 3 或多于 5 **警告**仍可跑（维护者自负） |
| 排序          | 按文件名前缀数字升序；解析失败则警告并按字典序            |

模块模式在单视频流水线之上增加：**模块层结构合并**与**跨视频嵌套检查**（见报告契约）。

### 2.3 分步子命令（调试，M1 起逐步提供）

```bash
lesson-review extract-audio <视频> -o <音频>
lesson-review transcribe <音频> -o <transcript.json>
lesson-review correct <transcript> -o <corrected.md>
lesson-review analyze <corrected> --mode single|module ...
```

子命令与 `run` 共用同一套配置与 manifest 字段定义。

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
    audio/                 # 若从视频抽取
    transcript_raw.json
    transcript_corrected.md
    structure.json         # 可选中间结构
    report.md              # 最终报告
    logs/
      pipeline.log
```

`run_id` 建议：`YYYYMMDD-HHMMSS_<输入指纹短码>`，便于并排对比多次迭代。

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

| 版本 | 日期       | 说明     |
| ---- | ---------- | -------- |
| v0.1 | 2026-07-23 | 首版契约 |
