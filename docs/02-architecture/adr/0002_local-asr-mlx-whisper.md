# ADR-0002：本地 ASR 使用 mlx-whisper

- **Status**：Accepted
- **Date**：2026-07-23

## Context

课例含未公开授课内容与学员声音，优先降低外发面。维护者设备为 Apple M5、24GB 内存，适合 MLX 加速。通用 `openai-whisper` 在 macOS 上默认 CPU 极慢；`faster-whisper` 对 Apple GPU 支持弱。千问 / DeepSeek 提供的是 LLM，不是本流水线首选 ASR。

## Options considered

| 选项                               | 优点                     | 缺点                                |
| ---------------------------------- | ------------------------ | ----------------------------------- |
| mlx-whisper（默认 large-v3-turbo） | 本地、快、隐私、无按量费 | 绑定 Apple Silicon 为主；需下载权重 |
| 云端 ASR API                       | 免本地算力、跨平台       | 费用、合规、长音频上传              |
| whisper.cpp                        | C++ 性能好               | 与 Python 编排割裂；MVP 不必双栈    |

## Decision

MVP 转写使用 **mlx-whisper**，默认模型 **`mlx-community/whisper-large-v3-turbo`**，语言默认中文课堂。

## Consequences

### 正面

- 单节 45～90 分钟课例转写时间可接受；无 ASR API 成本。
- 原始音频不必上传第三方（仅 LLM 步骤发送文本）。

### 负面

- 首次需下载约 1.6GB 权重；需安装 ffmpeg。
- Windows / Linux 开发机需后续 ADR（云端 ASR 或 faster-whisper）。
- **跨平台说明**：默认本机 Mac（Apple Silicon）ASR；其他平台另开 ADR，不在本决策内承诺。

### 相关

- 技术摘要：`docs/02-architecture/002_tech-stack_技术选型摘要.md`
