# batch-conduct 言行扫描速查

- **版本**：v0.2
- **日期**：2026-08-06
- **用途**：对目录内多段视频依次转写、纠错，并扫描粗俗辱骂、诋毁学科或课程、贬低前任讲师等表述；非课评教练主路径
- **契约**：`docs/01-product/002_cli-contract_CLI命令与运行契约.md`（`batch-conduct`）
- **上游**：薄标准 §5 分类索引；判定全文见备课方法 A07

## 学习目标

- 能对一个含多段编号视频的目录跑通 `batch-conduct`。
- 能说明产出目录位置，并正确阅读 `summary.md`（含建议处置路径）。
- 理解边界：对事不对人；媒体不入库；工具不代替人事处分。

## 问题与价值

投诉或巡课有时只需**摘句证据**与处置建议，不必跑完整课评报告。本命令停在纠错与言行扫描，比完整课评更省时，且结果可按目录汇总（对齐八月 O4 · KR4.2）。

## 用法

```bash
# 目录内 mp4/音频按文件名前缀数字排序后依次处理
uv run lesson-review batch-conduct "data/input/<某目录>"

# 冒烟：只跑前 N 个
uv run lesson-review batch-conduct "data/input/<某目录>" --limit 1
```

产出根目录：`output/conduct_YYYYMMDD-HHMMSS/`

| 文件                          | 说明                           |
| ----------------------------- | ------------------------------ |
| `summary.md`                  | 全目录 findings 汇总（优先读） |
| `batch_manifest.json`         | 批次元数据                     |
| `NN_<stem>/transcript_*`      | 原始转写 / 纠错稿              |
| `NN_<stem>/conduct_scan.json` | 单段扫描 JSON（含处置路径）    |

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

## 排查

| 现象                  | 处理方向                                                    |
| --------------------- | ----------------------------------------------------------- |
| `LLM_API_KEY missing` | 本地 `.env` 按 `.env.example` 配置                          |
| 非法媒体后缀被跳过    | 仅处理视频/音频后缀；检查目录内容                           |
| 单段失败但批处理继续  | 看该段 `error` 与终端日志；可单独重跑该文件                 |
| 扫描漏报「卧槽」等    | 对照 `transcript_corrected.md` 与 raw；维护者可人工检索核对 |

## 相关文档

- [CLI 契约](../01-product/002_cli-contract_CLI命令与运行契约.md)
- [PRD §3.6 旁路能力](../01-product/001_prd_课评教练MVP产品说明.md)
- [单视频课评跑通](./005_single-video-run_单视频课评跑通说明.md)
- [本仓开发闭环](./003_cli-dev-loop_本仓开发闭环.md)
