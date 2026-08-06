# 开发环境与 uv

- **版本**：v0.3.1
- **日期**：2026-08-06
- **用途**：本机可复现环境说明（含专利 / 软著材料中的「构建与运行环境」摘要）
- **读者**：维护者；后续协作者

---

## 1. 已验证的本机基线（维护者）

| 组件           | 版本 / 说明                                 |
| -------------- | ------------------------------------------- |
| 硬件           | Apple Silicon（如 M5）· 统一内存 24GB       |
| 包管理         | Homebrew（`/opt/homebrew`）                 |
| Python（项目） | **3.12.x**（`brew install python@3.12`）    |
| 编排工具       | **uv**（`brew install uv`）                 |
| Node（仅文档） | 用于 Prettier / markdownlint，见根 `README` |

系统自带的 `/usr/bin/python3` 多为 **3.9.x**。这是正常现象：Homebrew 的 `python@3.12` **不会**覆盖命令名 `python3`，只提供 `python3.12`。本仓以 **uv + `.python-version`** 为准，不要求改系统默认 `python3`。

---

## 2. 一次性：让 Homebrew 进入 PATH

zsh 登录配置（推荐，Homebrew 官方写法）：

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

新开终端后自检：

```bash
which brew
which python3.12
which uv
python3.12 --version   # 期望 3.12.x
python3 --version       # 可能仍是系统 3.9.x，可忽略
uv --version
```

别名与提示符等交互配置继续放在 `~/.zshrc`；**PATH / brew** 放在 `~/.zprofile`。

---

## 3. 本仓：用 uv 钉死 Python 3.12

仓库根目录有 `.python-version`（内容为 `3.12`）。在仓库内：

```bash
cd /path/to/lesson-review-ai
uv python install 3.12    # 若本机尚无 uv 管理的 3.12
uv python pin 3.12        # 已有 .python-version 时可省略或重跑
```

后续实现阶段日常用：

```bash
uv sync                   # 按锁文件安装依赖
uv run lesson-review --help
uv run lesson-review check
uv run lesson-review run <媒体文件> --dry-run
```

确认解释器：

```bash
uv run python --version   # 期望输出 Python 3.12.x
```

说明：`uv python install 3.12` 会再下一份独立解释器；若下载较慢，可直接让 uv 使用 Homebrew 的 `python3.12`（本仓已验证可行）。

---

## 4. 运行时依赖（流水线）

| 依赖             | 安装                                               | 用途               |
| ---------------- | -------------------------------------------------- | ------------------ |
| ffmpeg           | `brew install ffmpeg`                              | 视频抽轨           |
| mlx-whisper      | ASR 相关依赖将在后续开发里程碑中通过 `uv add` 引入 | 本地 ASR           |
| DeepSeek API Key | 复制 `.env.example` → `.env` 后填写                | 纠错 / 结构 / 建议 |

`ffmpeg` 安装后自检：

```bash
ffmpeg -version
uv run lesson-review check   # 应显示 ffmpeg OK
```

---

## 5. Markdown 工具链（文档）

与代码环境独立，仍用 Node：

```bash
npm install
npm run format
npm run lint:md
```

详见根 `README`「Markdown 工具链」一节。

---

## 6. 与里程碑的关系

| 里程碑          | 环境相关交付                                                  |
| --------------- | ------------------------------------------------------------- |
| M0              | 文档 + Markdown lint（已合入）                                |
| **M0b（本文）** | uv / Python 3.12 说明与版本钉死；ffmpeg 安装指引              |
| M1              | `pyproject.toml`、CLI 骨架、`--dry-run` / `check`（已有骨架） |

工具上手与排障短文见 [`docs/90-guides/`](../90-guides/README.md)（非产品源）。

---

## 7. 修订记录

| 版本   | 日期       | 说明                                            |
| ------ | ---------- | ----------------------------------------------- |
| v0.1   | 2026-07-24 | 首版环境说明                                    |
| v0.2   | 2026-07-24 | ffmpeg 已可用；补充 `uv run lesson-review` 命令 |
| v0.3   | 2026-07-24 | 链到 `docs/90-guides/`                          |
| v0.3.1 | 2026-08-06 | 可读性润色：mlx-whisper 安装说明补全            |
