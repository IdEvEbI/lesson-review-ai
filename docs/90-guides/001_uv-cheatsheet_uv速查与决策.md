# uv：问题、用法与进阶

- **版本**：v0.3
- **日期**：2026-07-24
- **官方文档**：[uv — Working on projects](https://docs.astral.sh/uv/guides/projects/) · [Installation](https://docs.astral.sh/uv/getting-started/installation/)

---

## 1. 学习目标

读完本文后，应当能够：

1. 说明解释器、虚拟环境（`.venv`）与锁文件（`uv.lock`）的分工；
2. 在本仓库执行 `uv sync` 与 `uv run lesson-review check`，并依据输出判断是否成功；
3. 在 Homebrew 提供的 Python 3.12 与 `uv python install` 之间作出合理选择。

---

## 2. 问题与价值

Python 项目在多人、多机器环境下常见如下问题：系统自带的 `python3` 版本过旧（在 macOS 上常见为 3.9）；使用全局 `pip` 安装依赖易造成环境污染或项目间冲突；缺少锁文件时，不同环境解析到的依赖版本不一致。

uv 用于统一管理本项目的 Python 解释器约定、虚拟环境与依赖锁定，使本地开发与锁文件描述保持一致。本仓库的日常入口为 `uv sync` 与 `uv run …`。

### 2.1 核心概念

| 概念     | 含义                                     | 在本仓库中的落点                                 |
| -------- | ---------------------------------------- | ------------------------------------------------ |
| 解释器   | 执行 Python 代码的运行时（例如 3.12.x）  | Homebrew 的 `python3.12`，或由 uv 安装的 CPython |
| 虚拟环境 | 项目隔离的依赖安装目录                   | 仓库根目录 `.venv/`（已列入 `.gitignore`）       |
| 锁文件   | 依赖解析后的精确版本清单，应纳入版本控制 | `uv.lock`；需求声明见 `pyproject.toml`           |

关系概览：

```text
.python-version（约定 3.12）
        ↓
   创建 / 使用 .venv
pyproject.toml（声明直接依赖）
        ↓
   uv 解析并写入 uv.lock
        ↓
   依赖安装到 .venv
业务命令：uv run <命令>（执行前对齐 lock 与环境）
```

---

## 3. 与同类方案的比较

| 方案                      | 特点                                 | 与本仓库选型的关系                            |
| ------------------------- | ------------------------------------ | --------------------------------------------- |
| pip + venv + requirements | 经典、工具链分散                     | 命令分散，且依赖锁定能力较弱                  |
| Poetry                    | 项目与依赖管理一体化                 | 能力接近；本仓选用 uv，侧重速度及可管理解释器 |
| conda                     | 适合数据科学及大量非 Python 原生依赖 | 对本仓库这类 Python CLI 项目而言过于复杂      |

本仓库为单人维护的 Python CLI：以 uv、锁文件与 `uv run` 作为默认工具链即可满足可复现需求。

---

## 4. 在本仓库中的用法

以下命令均在仓库根目录执行。请先确保 Homebrew 已加入 `PATH`（见 [开发环境与 uv](../03-delivery/003_dev-environment_开发环境与uv.md)）。

### 4.1 首次克隆或更换机器

```bash
cd /path/to/lesson-review-ai
uv sync
uv run python --version
uv run lesson-review --help
```

**预期结果**：`python --version` 显示 3.12.x；`--help` 列出 `version`、`run`、`check` 等子命令。

### 4.2 检查运行依赖（不调用模型）

```bash
uv run lesson-review check
```

**预期结果**：至少出现 `[OK] ffmpeg …`。在骨架阶段，`mlx-whisper` 与 `LLM_API_KEY` 可以为 `[MISSING]`（标记为 optional）。

### 4.3 对单个媒体文件执行 dry-run

```bash
uv run lesson-review run /path/to/sample.wav --dry-run
```

**预期结果**：输入与 ffmpeg 为 OK，进程退出码为 `0`。路径不存在或后缀不受支持时，退出码为 `1`。

### 4.4 向项目添加 Python 依赖

```bash
uv add <package>
uv run python -c "import <package>; print('ok')"
```

该操作会修改 `pyproject.toml` 与 `uv.lock`，应在同一变更中提交。

### 4.5 解释器来源的选择

| 条件                                            | 建议                                                 |
| ----------------------------------------------- | ---------------------------------------------------- |
| 已安装 Homebrew `python@3.12`，且 `uv run` 正常 | 保持现状即可                                         |
| 需要由 uv 管理独立解释器，且网络可用            | 执行 `uv python install 3.12`                        |
| `uv python install` 长时间无进展                | 中止该命令，改用 Homebrew 3.12；**无需修改仓库配置** |

查看当前 `uv run` 使用的解释器路径：

```bash
uv run python -c "import sys; print(sys.executable)"
```

---

## 5. 常见问题与排查

| 现象                                    | 处理方向                                              |
| --------------------------------------- | ----------------------------------------------------- |
| `python3 --version` 仍为 3.9            | 属预期；请检查 `python3.12` 与 `uv run python`        |
| 直接执行 `lesson-review` 提示未找到命令 | 使用 `uv run lesson-review`，或先执行 `uv sync`       |
| `ModuleNotFoundError`                   | 确认当前目录为仓库根目录，并已执行 `uv sync`          |
| 与其他环境依赖不一致                    | 确认使用最新 `uv.lock`；避免使用全局 pip 向本项目装包 |
| `uv python install` 失败或过慢          | 检查网络；改用 Homebrew 3.12                          |

---

## 6. 进一步学习路径

1. 阅读官方文档 [Working on projects](https://docs.astral.sh/uv/guides/projects/)。
2. 对照本仓库 `pyproject.toml` 中的 `dependencies` 与 `[project.scripts]`。
3. 如需系统了解包装规范，再查阅 Python Packaging User Guide 中与项目元数据、锁文件相关的章节。

当前阶段不必优先学习：向 PyPI 发布软件包、完整 PEP 文本、conda 生态。

---

## 7. 相关文档

- [开发环境与 uv](../03-delivery/003_dev-environment_开发环境与uv.md)
- [本仓开发闭环](./003_cli-dev-loop_本仓开发闭环.md)
- [ffmpeg：问题、用法与进阶](./002_ffmpeg-basics_抽轨速查.md)
