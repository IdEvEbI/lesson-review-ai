# Architecture Decision Records（ADR）

- **用途**：本目录记录显著架构决策的背景、备选方案与后果（对齐 AWS / Microsoft 等实践中的 ADR 模式）。
- **规则**：不删除既有 ADR；若决策变更，应新建条目并标记 **Supersedes** 指向被取代者。
- **模板**：采用精简 Nygard 格式（Status / Context / Decision / Consequences）。

| ID                                               | 标题                         | 状态     |
| ------------------------------------------------ | ---------------------------- | -------- |
| [0001](./0001_python-cli-monolith.md)            | Python CLI 单体              | Accepted |
| [0002](./0002_local-asr-mlx-whisper.md)          | 本地 ASR：mlx-whisper        | Accepted |
| [0003](./0003_llm-deepseek-openai-compatible.md) | LLM：DeepSeek（OpenAI 兼容） | Accepted |
| [0004](./0004_two-pass-knowledge-review.md)      | 专业预审两段式与假阳性闸门   | Accepted |
| [0005](./0005_clarity-and-playback-boundary.md)  | 讲清度、待回放与表达噪声闸门 | Accepted |
| [0006](./0006_lab-pedagogy-checks.md)            | 实操课三条套路与课型推断     | Accepted |
