# ADR-0001：Python CLI 单体

- **Status**：Accepted
- **Date**：2026-07-23

## Context

课评 MVP 第一用户仅维护者一人；需要快速演示竖切、迭代提示词。团队规模小，无专职 SRE。维护者熟悉 Python，C++ 可作为 ASR 备选但会增加首版交付时间。

## Decision

采用 **Python 3.11+** 实现 **单仓库 CLI 单体**：编排、LLM 调用、报告生成均在同一进程（或同包）内完成，不引入微服务、消息队列或 Web 服务。

## Consequences

### 正面

- 开发与调试路径短；与 mlx-whisper、OpenAI SDK 集成简单。
- 部署即「克隆仓库 + 虚拟环境 + `.env`」。

### 负面

- 长课例批处理时单进程占用高；模块并行需后续优化。
- 非 macOS 环境需另验证 ASR 路径（可能需云端 ASR ADR）。

### 相关

- 产品契约：`docs/01-product/002_cli-contract_CLI命令与运行契约.md`
