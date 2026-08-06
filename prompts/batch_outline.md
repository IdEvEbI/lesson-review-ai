# 批处理讲解结构提纲（batch_outline）

- **版本**：v0.1
- **用途**：从纠错逐字稿提炼少量讲解节点，供 `batch-conduct --with-outline` 写入 summary；观察点散 / 缺主线
- **边界**：不是 Pass A；不是教练报告；不要评判知识对错或教师个人

## 输出（仅 JSON）

```json
{
  "nodes": [
    {
      "title": "节点短标题",
      "start_s": 0,
      "one_liner": "一句说明本节点在讲什么"
    }
  ],
  "mainline": "一句话概括本段主线（若转写看不清写「转写未体现主线」）",
  "scatter_note": "若明显点多且散，写一句；否则空字符串"
}
```

## 约束

1. 节点数 **5～12**；宁少勿凑。
2. **不要编造 `start_s` 时间戳**（当前实现也不会把时间写入 summary）；无法从转写可靠对齐时省略该字段或填 `null`。
3. 禁止编造未出现的章节；缺口用 `scatter_note` / `mainline` 说明。
4. 对事不对人；不要输出 Markdown 包裹。
