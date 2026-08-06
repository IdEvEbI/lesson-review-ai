# ADR-0001：Python CLI 单体

- **Status**：Accepted
- **Date**：2026-07-23

## Context

课评 MVP 的第一用户仅为维护者本人，需要快速演示竖切并迭代提示词。团队规模小，没有专职 SRE。维护者熟悉 Python；C++ 可作为 ASR 备选实现，但会拉长首版交付时间。

## Decision

采用 **Python 3.11+** 实现 **单仓库 CLI 单体**：编排、LLM 调用与报告生成均在同一进程（或同一包）内完成，不引入微服务、消息队列或 Web 服务。

## Consequences

### 正面

- 开发与调试路径短，与 mlx-whisper、OpenAI 兼容 SDK 的集成简单。
- 部署方式即为「克隆仓库 + 虚拟环境 + `.env`」。

### 负面

- 长课例批处理时，单进程资源占用偏高；模块并行需后续优化。
- 非 macOS 环境需另行验证 ASR 路径（可能需要云端 ASR 的 ADR）。

### 相关

- 产品契约：`docs/01-product/002_cli-contract_CLI命令与运行契约.md`
