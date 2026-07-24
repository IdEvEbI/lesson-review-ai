# lesson-review-ai · 课评 AI

- **定位**：把授课视频 / 音频变成「纠错逐字稿 + 结构要点 + 可执行提升建议」的工程仓
- **维护者**：本仓维护者（质量架构师 / 发现者 / AI 先行者）
- **标准与方法上游**：[teaching-quality-enablement](https://github.com/IdEvEbI/teaching-quality-enablement)（业务文档仓；口径以那边为准）
- **愿景摘要入口（上游）**：`docs/00-定位与方法/005_lesson-review-ai_课评AI愿景与MVP边界.md`

> 本仓负责**可运行流水线**；好课标准、带教路径、三不三要等业务真相在上游文档仓，不在这里另起一套。本仓为 public 仓库，文档不写维护者真名、所在机构或对外品牌名。

---

## 1. 目标（MVP）

1. 输入 **1 个视频**，或同一知识模块下**手动选定**的 **3～5 个视频**。
2. 模块内按文件名**前缀数字**升序处理。
3. 跑通：分离音轨（若需要）→ 转写 → 纠错 → 提炼结构与要点 → 输出提升建议与改法。
4. 模块模式输出**模块层 + 视频层**结构，并检查总分总及嵌套关系上的明显缺口。
5. 第一用户是维护者本人；报告默认私密，用于迭代提示词与口径。

当前**不做**：全员自查门户、自动归模块、生成正式授课成片、绩效考核联动。详见 [产品 PRD](./docs/01-product/001_prd_课评教练MVP产品说明.md)。

---

## 2. 新会话请先读

1. [产品 PRD](./docs/01-product/001_prd_课评教练MVP产品说明.md)（范围、用户、验收）
2. [上游标准引用](./docs/02-architecture/003_upstream-standards_上游标准引用.md)
3. [架构概览](./docs/02-architecture/001_system-overview_系统概览.md) · [Issue 地图](./docs/03-delivery/001_issue-map_竖切与Issue清单.md) · [DevOps 工作流](./docs/03-delivery/002_devops-workflow_分支PR与门禁.md)
4. 文档总入口：[docs/README.md](./docs/README.md)
5. Cursor Rule：`.cursor/rules/lesson-review-ai.mdc`

**默认技术栈**：Python CLI（uv）· 本地 mlx-whisper · DeepSeek API（见 [技术选型](./docs/02-architecture/002_tech-stack_技术选型摘要.md)）

**开发环境**：见 [开发环境与 uv](./docs/03-delivery/003_dev-environment_开发环境与uv.md)（`python3` 可能仍是系统 3.9；项目用 `python3.12` / `uv`）。

---

## 3. Markdown 工具链

与上游文档仓对齐：Prettier + `prettier-plugin-zh` + markdownlint。编辑器安装推荐扩展后，保存 Markdown 会自动格式化（含中英文空格）。

```bash
npm install
npm run format      # 格式化
npm run lint:md     # Markdownlint 检查
```

提交前请确保 `npm run format:check` 与 `npm run lint:md` 均通过。CI 工作流：`.github/workflows/docs-lint.yml`。

---

## 4. 建议的技术骨架（实现时可调整）

| 步骤               | 建议方向（非锁死）                             |
| ------------------ | ---------------------------------------------- |
| 音视频             | `ffmpeg` 抽音轨（`brew install ffmpeg`）       |
| 转写               | 本地 **mlx-whisper**（large-v3-turbo）         |
| 纠错 / 结构 / 建议 | **DeepSeek API** + 版本化提示词（`prompts/`）  |
| 编排               | 先 CLI / 脚本；跑通后再加简易界面              |
| 产物               | `output/` 下 Markdown 报告；不提交真实课例媒体 |

Python 包与 CLI 在 **M1** 落地。环境配好后：

```bash
uv sync
uv run lesson-review --help
uv run lesson-review check
```

详见 [开发环境与 uv](./docs/03-delivery/003_dev-environment_开发环境与uv.md)。

---

## 5. 隐私

- 真实学员脸、工号、未脱敏对话默认不进 Git。
- API Key、模型密钥只放本地环境变量或私钥文件（已进 `.gitignore`）。
- 对外演示用脱敏或自制样例音视频。
- public 仓库中不写维护者真名、所在机构或对外品牌名。
