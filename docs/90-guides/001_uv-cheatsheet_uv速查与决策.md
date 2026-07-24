# uv 速查与决策

- **版本**：v0.1
- **日期**：2026-07-24
- **官方文档**：[uv — Working on projects](https://docs.astral.sh/uv/guides/projects/)

---

## 1. uv 在本仓扮演什么角色

一句话：**管本项目的 Python 版本约定 + 虚拟环境 + 依赖锁文件**，让「你机器上跑的」和「锁文件写的」一致。

| 文件 / 目录       | 作用                           |
| ----------------- | ------------------------------ |
| `.python-version` | 钉大版本（本仓 `3.12`）        |
| `pyproject.toml`  | 声明直接依赖与入口脚本         |
| `uv.lock`         | 锁住解析后的精确版本（应提交） |
| `.venv/`          | 本地虚拟环境（不提交）         |

不必先 `source .venv/bin/activate`；优先用 `uv run …`，它会按需同步环境再执行。

---

## 2. 日常命令（够用集）

在仓库根目录：

```bash
uv sync                          # 按 lock 安装/对齐依赖
uv run python --version          # 看当前项目用的解释器
uv run lesson-review --help      # 跑本仓 CLI
uv run lesson-review check
uv add <包名>                    # 加依赖并改 pyproject + lock
uv remove <包名>                 # 移除依赖
uv lock                          # 仅刷新锁（一般 add/sync 会带上）
```

成功判据：`uv run lesson-review --help` 能打印命令列表，且无 `ModuleNotFoundError`。

---

## 3. 决策：brew 的 Python，还是 `uv python install`？

两者都提供 **3.12**，对本仓都合法。

| 选项                     | 何时选                                      | 注意                                                   |
| ------------------------ | ------------------------------------------- | ------------------------------------------------------ |
| Homebrew `python@3.12`   | 本机已装、或 `uv python install` 下载很慢   | `python3` 仍可能是系统 3.9；用 `python3.12` / `uv run` |
| `uv python install 3.12` | 想要 uv 自管的一份独立解释器（CI/多机更齐） | 需能访问 uv 的 Python 构建源；慢时不必硬等             |

**规范点**是：版本钉在 3.12 + 有 `uv.lock` + 用 `uv run`，**不是**必须用 uv 下载的那份二进制。

自检「项目到底用哪份」：

```bash
uv run python -c "import sys; print(sys.executable)"
```

---

## 4. 坏了怎么想

| 现象                               | 先查                                                      |
| ---------------------------------- | --------------------------------------------------------- |
| `python3` 仍是 3.9                 | 正常；看 `python3.12` 与 `uv run python`                  |
| `lesson-review: command not found` | 用 `uv run lesson-review`，或先 `uv sync`                 |
| 依赖版本和别人不一致               | 是否提交/拉取了最新 `uv.lock`？是否绕过 uv 用了全局 pip？ |
| `uv python install` 一直转圈       | 网络/代理；可改用 brew 3.12，仓库配置不用改               |

---

## 5. 和本仓其他文档的关系

- 装机门禁：[开发环境与 uv](../03-delivery/003_dev-environment_开发环境与uv.md)
- 改完代码怎么跑：[本仓开发闭环](./003_cli-dev-loop_本仓开发闭环.md)
