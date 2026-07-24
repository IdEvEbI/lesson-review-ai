# ADR-0003：LLM 使用 DeepSeek（OpenAI 兼容接口）

- **Status**：Accepted
- **Date**：2026-07-23

## Context

纠错、结构提炼与教练建议依赖长上下文中文理解与稳定 JSON/Markdown 输出。维护者可申请国内 API；MVP 以性价比与接入速度为主。本地 24GB 可跑小模型，但课评质量通常不及云端旗舰，且调优成本高。

## Options considered

| 选项               | 优点                        | 缺点                 |
| ------------------ | --------------------------- | -------------------- |
| DeepSeek V4 Flash  | 低价、OpenAI 兼容、长上下文 | 需外发逐字稿文本     |
| DeepSeek V4 Pro    | 建议质量更高                | 单价高于 Flash       |
| 通义千问 DashScope | 阿里云生态、企业采购        | 需单独对接与定价熟悉 |
| OpenAI / Claude    | 质量参照强                  | MVP 日常成本偏高     |

## Decision

默认 **DeepSeek API**（`https://api.deepseek.com`，OpenAI SDK 兼容），默认模型 **V4 Flash**；质量不足时对单步或全链升级 **V4 Pro**。通过环境变量保留切换至 DashScope 等兼容端点的能力。

## Consequences

### 正面

- 单课例多次 prompt 迭代成本可控；系统提示词可利用缓存降价。
- 与主流 SDK 一致，替换供应商成本低。

### 负面

- 逐字稿需传输至 DeepSeek；须遵守组织数据与密钥管理要求。
- 供应商调价或限流时需监控；manifest 记录 model id 便于回溯。

### 相关

- `.env.example` 中的 `LLM_*` 变量
- 产品 PRD 非功能需求：隐私与可替换
