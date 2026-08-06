# batch-conduct 言行扫描速查

- **版本**：v0.1
- **日期**：2026-07-29
- **用途**：目录内多段视频 → 转写 → 纠错 → 扫描脏话 / 贬低前任讲师；**非**课评教练主路径
- **契约**：`docs/01-product/002_cli-contract_CLI命令与运行契约.md`（`batch-conduct`）

## 学习目标

- 能对一个含多段编号视频的目录跑通 `batch-conduct`。
- 知道产出在哪、如何读 `summary.md`，以及边界（对事不对人、媒体不入库）。

## 问题与价值

投诉或巡课有时只需**摘句证据**（是否脏话、是否贬低前任/其他讲师），不必跑完整课评报告。本命令停在纠错 + 言行扫描，省时且结果可汇总。

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
| `NN_<stem>/conduct_scan.json` | 单段扫描 JSON                  |

## 约束

- 真实课例与 `output/` **不进 Git**；公开文档与提交不写老师真名、校区名、品牌名。
- 报告口径：对事不对人；有摘句才算 finding；汇总仅供维护者私下对齐。
- 纠错提示词要求**保留**脏话原词，避免洗证据。

## 排查

| 现象                  | 处理方向                                          |
| --------------------- | ------------------------------------------------- |
| `LLM_API_KEY missing` | 本地 `.env` 按 `.env.example` 配置                |
| 非法媒体后缀被跳过    | 仅处理视频/音频后缀；检查目录内容                 |
| 单段失败但批处理继续  | 看该段 `error` 与终端日志；可单独重跑该文件       |
| 扫描漏报「卧槽」等    | 对照 `transcript_corrected.md` 与 raw；可人工检索 |

## 相关文档

- [CLI 契约](../01-product/002_cli-contract_CLI命令与运行契约.md)
- [PRD §3.5 旁路能力](../01-product/001_prd_课评教练MVP产品说明.md)
- [本仓开发闭环](./003_cli-dev-loop_本仓开发闭环.md)
