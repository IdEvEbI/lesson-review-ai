# Architecture Decision Records（ADR）

- **用途**：记录**显著架构决策**的背景、选项与后果（AWS / Microsoft 等实践中的 ADR 模式）。
- **规则**：不删除旧 ADR；变更时新建并标记 **Supersedes**。
- **模板**：采用精简 Nygard 格式（Status / Context / Decision / Consequences）。

| ID                                               | 标题                         | 状态     |
| ------------------------------------------------ | ---------------------------- | -------- |
| [0001](./0001_python-cli-monolith.md)            | Python CLI 单体              | Accepted |
| [0002](./0002_local-asr-mlx-whisper.md)          | 本地 ASR：mlx-whisper        | Accepted |
| [0003](./0003_llm-deepseek-openai-compatible.md) | LLM：DeepSeek（OpenAI 兼容） | Accepted |
| [0004](./0004_two-pass-knowledge-review.md)      | 专业预审两段式与假阳性闸门   | Accepted |
| [0005](./0005_clarity-and-playback-boundary.md)  | 讲清度、待回放与表达噪声闸门 | Accepted |
