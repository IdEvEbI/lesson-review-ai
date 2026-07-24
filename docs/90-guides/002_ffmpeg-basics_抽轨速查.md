# ffmpeg 抽轨速查

- **版本**：v0.1
- **日期**：2026-07-24
- **官方**：[FFmpeg](https://ffmpeg.org/documentation.html) · 本机安装：`brew install ffmpeg`

---

## 1. 本仓为什么需要它

课评流水线第一步：若输入是**视频**，先抽出音轨，再交给本地 ASR（mlx-whisper）。已是音频则可跳过抽轨。

MVP 不自己实现解码器；**调用系统里的 `ffmpeg` 可执行文件**（见 CLI 契约与 ADR）。

---

## 2. 本机自检

```bash
which ffmpeg
ffmpeg -version
uv run lesson-review check
```

成功判据：

- `which` 指向 Homebrew（常见 `/opt/homebrew/bin/ffmpeg`）
- `lesson-review check` 里 ffmpeg 一行为 `[OK]`

未安装：

```bash
brew install ffmpeg
```

---

## 3. 你需要会的「判断」，不是背全部参数

| 问题                         | 判断                                                               |
| ---------------------------- | ------------------------------------------------------------------ |
| 输入是 mp4 还是 wav？        | 视频 → 需要抽轨；纯音频 → 可跳过                                   |
| dry-run 已过，正式跑却失败？ | 先看退出码 2（依赖）还是 3（流水线步骤）；ffmpeg 缺失属依赖        |
| 要不要手写一条 ffmpeg？      | 调试时可手写；产品路径应由 `lesson-review` 封装（后续 media 切片） |

调试示例（可选，理解用；正式以 CLI 为准）：

```bash
ffmpeg -i input.mp4 -vn -acodec copy output.m4a
```

不同容器/编码可能要改参数；封装进本仓后以代码与文档为准。

---

## 4. 隐私与仓库

真实课例音视频**不进 Git**（已在 `.gitignore`）。只在本地 `data/input/` 或任意路径放置，用 CLI 读路径。

---

## 5. 相关文档

- [本仓开发闭环](./003_cli-dev-loop_本仓开发闭环.md)
- [CLI 契约](../01-product/002_cli-contract_CLI命令与运行契约.md)
