# batch-conduct 言行扫描速查

- **版本**：v0.4.1
- **日期**：2026-08-06
- **用途**：对目录内多段视频依次转写、纠错，并扫描粗俗辱骂、诋毁学科或课程、贬低前任讲师等表述；并汇总时长与细课型日分布（旁路增强）；非课评教练主路径
- **契约**：`docs/01-product/002_cli-contract_CLI命令与运行契约.md`（`batch-conduct`）
- **上游**：薄标准 §5 分类索引；判定全文见备课方法 A07；细课型对齐备课方法 `004`～`010`

## 学习目标

- 能对一个含多段编号视频的目录跑通 `batch-conduct`。
- 能说明产出目录位置，并正确阅读 `summary.md`（时长、细课型占比、言行 findings、可选结构提纲）。
- 理解边界：对事不对人；媒体不入库；工具不代替人事处分；细课型可标 `other` 再由维护者校准。

## 问题与价值

投诉或巡课有时只需**摘句证据**与处置建议，不必跑完整课评报告。批处理还可回答：「这一天各段多长？偏开场/原理还是代码/项目？点是否散？」——用时长与细课型分布辅助判断，而不是只扫脏话。

口径提醒：老师「说话有底气」属声音状态线索，**不等于**讲解有逻辑；逻辑与主线问题看结构提纲与课型时长分布，不靠声学打合格分。

## 用法

```bash
# 目录内 mp4/音频按文件名前缀数字排序后依次处理
uv run lesson-review batch-conduct "data/input/<某目录>"

# 冒烟：只跑前 N 个
uv run lesson-review batch-conduct "data/input/<某目录>" --limit 1

# （规划）追加各段讲解结构提纲
uv run lesson-review batch-conduct "data/input/<某目录>" --with-outline

# 对已有批产出补时长与细课型（不重跑 Whisper）
uv run lesson-review batch-enrich "output/<课例目录>"

# 人工改 pedagogy_type.json 的 source=override 后重渲
uv run lesson-review batch-refresh-summary "output/<课例目录>"
```

产出根目录：与输入目录**同名**，便于对照查找：

```text
data/input/<课例目录>/
output/<课例目录>/          # summary.md、batch_manifest.json、各段产物
```

同名目录已存在时加 `--force` 覆盖。若输入路径无有效目录名（极少见），回退为 `output/conduct_YYYYMMDD-HHMMSS/`。

| 文件                           | 说明                                   |
| ------------------------------ | -------------------------------------- |
| `summary.md`                   | 总览（时长 / 课型 / findings）优先读   |
| `batch_manifest.json`          | 批次元数据（含时长与 `pedagogy_type`） |
| `NN_<stem>/transcript_*`       | 原始转写 / 纠错稿                      |
| `NN_<stem>/conduct_scan.json`  | 单段扫描 JSON（含处置路径）            |
| `NN_<stem>/pedagogy_type.json` | （规划）细课型判定与置信说明           |
| `NN_<stem>/outline.md`         | （规划，`--with-outline`）讲解结构提纲 |

## 如何读 `summary.md`

1. **总览表**：序号、文件名、**时长**、细课型、言行 finding 数、状态。
2. **日分布**：各 `pedagogy_type` 的**时长占比**（不是视频个数占比）。开场/简介过长而代码/项目过短时，在此一眼可见。
3. **分文件言行**：既有 findings 表与处置路径。
4. **结构提纲**（若开启）：每段「主线 / 散点」用无序列表；其下**节点用有序列表**（`1.` / `2.`…），不要写成 `- 1.` 混排。节点**不展示**模型粗估时间戳（易与片长不符）。用于观察跳跃与缺主线，**不是** Pass A / 教练结论。

细课型取值：`004`～`010` 或 `other`。`other` 表示模型不敢判，请维护者校准后再解读分布。细课型**不**写入主路径 `lesson_type` 门禁。

## 日课对齐备忘（本地，不入库）

维护者可在 `output/<课例目录>/` 另存**校区对齐备忘**（对事不对人；公开仓库不提交）。备忘宜含：课型时长分布要点、可执行课程建议、给校区负责人的对齐短句。

**纠错稿闸门（与单视频 M1b 相同）**：写备忘或把 `summary.md` 当对齐依据前，须**通读**相关段 `transcript_corrected.md`，对照 summary / 提纲是否夸大完成度或主交付偏移；偏差写入同目录 `summary_修正记录.md`（不入库）。步骤与模板见 [005 §4](./005_single-video-run_单视频课评跑通说明.md)。**未过闸不得外发带教或当作校区对齐唯一依据。**

## 扫描类别与处置路径

| 类别                         | 含义（摘要）             |
| ---------------------------- | ------------------------ |
| `profanity`                  | 粗俗辱骂                 |
| `belittle_prior_teacher`     | 贬低前任 / 其他讲师      |
| `belittle_subject_or_course` | 诋毁本学科或本课程       |
| `other_conduct`              | 其他明显不当言行（可选） |

建议处置字段 `disposition_path`：`private_align` / `mentor_followup` / `evidence_only` / `playback_review` / `policy_manual_review`。详见 `prompts/conduct_scan.md`。

## 约束

- 真实课例与 `output/` **不进 Git**；公开文档与提交不写老师真名、校区名、品牌名。
- 报告口径：对事不对人；只有附带逐字稿摘句的项才可记为 finding；汇总仅供维护者私下对齐。
- 纠错提示词要求**保留**脏话原词，纠错阶段不得将脏话替换为委婉语，以免削弱摘句证据效力。
- 细课型不确定时标 `other`，禁止为美观硬猜。

## 排查

| 现象                  | 处理方向                                                    |
| --------------------- | ----------------------------------------------------------- |
| `LLM_API_KEY missing` | 本地 `.env` 按 `.env.example` 配置                          |
| 非法媒体后缀被跳过    | 仅处理视频/音频后缀；检查目录内容                           |
| 单段失败但批处理继续  | 看该段 `error` 与终端日志；可单独重跑该文件                 |
| 扫描漏报「卧槽」等    | 对照 `transcript_corrected.md` 与 raw；维护者可人工检索核对 |
| 时长为 0 或明显偏短   | 查 `ffprobe` / ASR segments；媒体是否损坏                   |
| 课型大量 `other`      | 正常保守行为；人工校准或补文件名线索后再判                  |

## 相关文档

- [CLI 契约](../01-product/002_cli-contract_CLI命令与运行契约.md)
- [PRD §3.6 旁路能力](../01-product/001_prd_课评教练MVP产品说明.md)
- [单视频课评跑通](./005_single-video-run_单视频课评跑通说明.md)
- [本仓开发闭环](./003_cli-dev-loop_本仓开发闭环.md)
