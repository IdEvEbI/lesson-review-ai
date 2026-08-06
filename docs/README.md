# 文档入口（lesson-review-ai）

业务愿景全文在上游仓 `teaching-quality-enablement`。本仓只保留工程所需摘要与契约，避免与上游长期双源漂移。

---

## 1. 产品（做什么、怎么验收）

请先阅读 [01-product/README.md](./01-product/README.md)。

MVP 范围以 [001 PRD](./01-product/001_prd_课评教练MVP产品说明.md) 为唯一产品源。

---

## 2. 架构与技术（怎么做、为什么）

请阅读 [02-architecture/README.md](./02-architecture/README.md)。

该目录包含系统概览、技术选型、[上游标准引用](./02-architecture/003_upstream-standards_上游标准引用.md) 与 ADR。

---

## 3. 交付（Issue、DevOps）

请阅读 [03-delivery/README.md](./03-delivery/README.md)。

该目录包含 Issue 地图、DevOps 约定与 [开发环境与 uv](./03-delivery/003_dev-environment_开发环境与uv.md)。

---

## 4. 学习与排障（非产品源）

请阅读 [90-guides/README.md](./90-guides/README.md)。

该目录提供 uv、ffmpeg 与本仓开发闭环短文。决定产品范围时，仍以 `01-product` 为准。

---

## 新会话推荐阅读顺序

1. `01-product/001` PRD：确认 MVP 做什么、不做什么。
2. `02-architecture/003` 上游标准引用：确认评价尺子从哪里来。
3. 若准备开始实现或改代码：阅读 `03-delivery/001` Issue 地图。
4. 若不熟悉 uv、ffmpeg 或本地 CLI：先阅读 `90-guides/`（单视频端到端见 `005`）。
5. 协作硬约束：阅读 `.cursor/rules/lesson-review-ai.mdc`。
