# ffmpeg：问题、用法与进阶

- **版本**：v0.3
- **日期**：2026-07-24
- **官方文档**：[FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- **本机安装**：`brew install ffmpeg`

---

## 1. 学习目标

读完本文后，应当能够：

1. 说明课评流水线为何需要 ffmpeg；
2. 完成本机安装校验，并使 `uv run lesson-review check` 中的 ffmpeg 项为 OK；
3. （可选）对本地短视频执行一次命令行抽轨，理解后续 CLI 将封装的步骤。

---

## 2. 问题与价值

授课录像通常为视频容器（同时包含画面与声音）。本仓库的语音识别（ASR）输入应为音频。若缺少可脚本化的抽轨手段，维护者往往只能依赖图形界面软件手动导出，或将文件上传至在线转换服务；前者难以纳入自动化，后者不利于课例隐私与结果复现。

ffmpeg 是通用的命令行多媒体处理工具，可完成解码、转封装、抽轨与转码等操作。本仓库 MVP 仅依赖其中与「自视频提取音轨」相关的能力，供本机转写使用。

---

## 3. 与同类方案的比较

| 方案                           | 特点                           | 与本仓库选型的关系                 |
| ------------------------------ | ------------------------------ | ---------------------------------- |
| 图形界面转换软件               | 操作直观                       | 难以脚本化，结果因人而异           |
| 在线转换服务                   | 无需本地安装                   | 课例外传风险高，不适合真实课堂材料 |
| 强制用户预先提供 wav           | 实现简单                       | 增加使用成本；输入以视频为常态     |
| 本机 ffmpeg，并由 CLI 封装调用 | 可脚本化、本地处理、过程可复现 | 与 ADR 及 CLI 契约一致             |

维护者无需成为音视频专家，但需要理解：ffmpeg 是流水线中的媒体预处理依赖；正式路径应由 `lesson-review` 调用，手工命令仅用于学习与排障。

---

## 4. 在本仓库中的用法

### 4.1 安装与校验

```bash
which ffmpeg
ffmpeg -version
uv run lesson-review check
```

**预期结果**：

- `which` 指向 Homebrew 路径（常见为 `/opt/homebrew/bin/ffmpeg`）；
- `check` 输出包含 `[OK] ffmpeg (required): …`。

若未安装：

```bash
brew install ffmpeg
```

### 4.2 手工抽轨（可选，用于理解）

准备一小段已脱敏的本地视频（例如桌面上的 `sample.mp4`），**不要**将真实课例提交至 Git：

```bash
ffmpeg -i ~/Desktop/sample.mp4 -vn -acodec copy ~/Desktop/sample.m4a
```

参数说明：`-i` 指定输入；`-vn` 丢弃视频轨；`-acodec copy` 尽量直接复制音频编码以加快处理。

若因编码不兼容导致失败，可改为重编码（更慢、兼容性更好）：

```bash
ffmpeg -i ~/Desktop/sample.mp4 -vn -ac 1 -ar 16000 ~/Desktop/sample.wav
```

**预期结果**：生成可播放的 `m4a` 或 `wav` 文件。

说明：产品路径中的抽轨将在后续 media 切片中由 CLI 封装；本节命令仅用于建立直观认识。

### 4.3 与 CLI dry-run 的关系

```bash
uv run lesson-review run ~/Desktop/sample.mp4 --dry-run
```

在骨架阶段，该命令主要校验输入后缀是否受支持、以及 ffmpeg 是否位于 `PATH`，不一定执行实际抽轨。当 ffmpeg 与 input 均为 OK 且退出码为 `0` 时，表示依赖门禁通过。

媒体文件应存放于本地任意路径或 `data/input/`（该目录已忽略），不得执行 `git add` 纳入版本库。

---

## 5. 常见问题与排查

| 现象                         | 处理方向                                              |
| ---------------------------- | ----------------------------------------------------- |
| `ffmpeg: command not found`  | 检查 PATH；执行 `brew install ffmpeg`                 |
| `check` 中 ffmpeg 为 MISSING | 同上；重新打开终端后再试                              |
| 手工抽轨失败                 | 阅读终端报错；尝试 wav 重编码命令；更换更短的测试文件 |
| dry-run 退出码为 2           | required 依赖缺失（常见为 ffmpeg）                    |
| dry-run 退出码为 1           | 路径错误，或后缀不在支持列表中                        |

---

## 6. 进一步学习路径

1. 查阅官方文档目录，按需检索具体参数。
2. 了解「容器格式」（如 mp4）与「编码格式」（如 aac）的区别，足以排查 `copy` 失败类问题。
3. 在 ASR 质量成为瓶颈时，再学习采样率、声道与响度等主题。

当前阶段不必优先学习：滤镜体系、直播推流、GPU 编解码调优。

---

## 7. 相关文档

- [本仓开发闭环](./003_cli-dev-loop_本仓开发闭环.md)
- [CLI 契约](../01-product/002_cli-contract_CLI命令与运行契约.md)
- [ADR-0002 本地 ASR](../02-architecture/adr/0002_local-asr-mlx-whisper.md)
