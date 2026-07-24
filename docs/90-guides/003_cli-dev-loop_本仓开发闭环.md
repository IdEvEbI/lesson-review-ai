# 本仓开发闭环：问题、用法与进阶

- **版本**：v0.3
- **日期**：2026-07-24
- **用途**：约定本仓库日常验证步骤，并以 CLI 退出码作为是否通过的客观依据

---

## 1. 学习目标

读完本文后，应当能够：

1. 按固定顺序完成 `uv sync`、`check` 与 `run --dry-run`；
2. 依据退出码 `0` / `1` / `2` 区分输入错误与依赖缺失；
3. 区分产品文档（`01-product`）与工具指南（`90-guides`）的阅读场景。

---

## 2. 问题与价值

在已安装 uv 与 ffmpeg 的前提下，仍可能出现：修改代码后未确认是否安装到当前环境；以对话结论代替终端结果；无法判断应查阅产品契约还是工具说明。

本文给出本仓库的**标准验证回路**，强调以终端输出与退出码作为判断依据。本文是仓库操作说明，不是通用工具评测。

---

## 3. 与其他文档的关系

| 文档类型   | 路径                    | 何时阅读                           |
| ---------- | ----------------------- | ---------------------------------- |
| 产品与验收 | `docs/01-product/`      | 变更范围、报告结构、CLI 契约含义时 |
| 架构与决策 | `docs/02-architecture/` | 变更技术选型或查阅 ADR 时          |
| 交付与协作 | `docs/03-delivery/`     | 分支、PR、Issue 与环境门禁时       |
| 工具入门   | `docs/90-guides/`       | 不熟悉 uv、ffmpeg 或本地命令时     |

`90-guides` 不是产品真相源；范围与验收以 PRD 为准。

---

## 4. 在本仓库中的用法

### 4.1 标准步骤

```text
进入仓库根目录
  → uv sync
  → uv run lesson-review --help
  → uv run lesson-review check
  → uv run lesson-review run <本地媒体路径> --dry-run
  →（若修改 Markdown）npm run format && npm run lint:md
  → 按 DevOps 约定开分支；提交须维护者明确授权
```

### 4.2 预期输出示例

```bash
uv sync
# 无 error 即可；环境已同步时可能很快结束

uv run lesson-review --help
# 应列出子命令：version / run / check

uv run lesson-review check
# [OK] ffmpeg (required): /opt/homebrew/bin/ffmpeg
# [MISSING] mlx-whisper (optional): ...
# [MISSING] LLM_API_KEY (optional): ...
# 在 required 项均 OK 时，退出码为 0
```

对本地音频执行 dry-run（路径请替换为实际文件）：

```bash
uv run lesson-review run /tmp/demo.wav --dry-run
# [OK] input ...
# [OK] ffmpeg ...
# Dry-run OK for required deps. Optional not ready: ...
# 退出码 0
```

输入不存在时：

```bash
uv run lesson-review run /tmp/no-such.wav --dry-run
# [MISSING] input ...
# 退出码 1
```

### 4.3 退出码含义

与 [CLI 契约](../01-product/002_cli-contract_CLI命令与运行契约.md) 一致：

| 退出码 | 含义           | 处理原则                            |
| ------ | -------------- | ----------------------------------- |
| 0      | 成功           | 门禁通过或命令正常结束              |
| 1      | 用户输入错误   | 修正路径或更换受支持的后缀          |
| 2      | 依赖缺失       | 先安装 required 依赖（例如 ffmpeg） |
| 3      | 流水线步骤失败 | 多见于转写或 LLM 调用（后续切片）   |

输出中的 `required` 与 `optional` 含义不同：骨架阶段允许 optional 项为 MISSING 且退出码仍为 `0`，不表示全部检查项必须为 OK 才能继续开发。

---

## 5. 常见问题与排查

| 现象                         | 处理方向                         |
| ---------------------------- | -------------------------------- |
| `uv run` 提示找不到模块      | 在仓库根目录执行 `uv sync`       |
| `check` 中 ffmpeg 为 MISSING | 按 ffmpeg 指南安装并检查 PATH    |
| dry-run 退出码为 1           | 检查文件是否存在、后缀是否受支持 |
| dry-run 退出码为 2           | 检查 required 依赖               |
| 仅对话声称成功、终端未验证   | 以退出码与本机输出为准           |

---

## 6. 进一步学习路径

1. 按本文完成一次完整 dry-run，并能解释各行输出。
2. 阅读 [DevOps 工作流](../03-delivery/002_devops-workflow_分支PR与门禁.md)。
3. 在 ASR / LLM 切片就绪后，再阅读计划中的 `004`（环境变量与 API Key）与 `005`（mlx-whisper）。

当前阶段不必优先学习：完整 pytest 体系、容器化部署（可留待工程化里程碑）。

---

## 7. 相关文档

- [uv：问题、用法与进阶](./001_uv-cheatsheet_uv速查与决策.md)
- [ffmpeg：问题、用法与进阶](./002_ffmpeg-basics_抽轨速查.md)
- [开发环境与 uv](../03-delivery/003_dev-environment_开发环境与uv.md)
