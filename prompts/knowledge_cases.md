# 专业知识与案例预审（knowledge_cases · Pass A）

- **版本**：v0.1
- **用途**：在标题锚点下预审知识准确性与案例恰当性，输出 JSON
- **上游**：授课力 V1 专业力（可观察部分）；报告契约 §3；ADR-0004
- **原则**：宁可漏报，不可错杀（假阳性优先于召回）

## 输入

用户消息提供：

1. `title_anchor`（视频标题 / 文件名 stem）
2. 纠错后逐字稿全文

## 输出

**只输出一个 JSON 对象**（不要 Markdown 前言；可用 ```json 代码块包裹）。字段：

```json
{
  "schema_version": 1,
  "title_anchor": "字符串",
  "anchor_strength": "strong|weak",
  "summary": "2～4 句摘要",
  "findings": [
    {
      "id": "k1",
      "category": "accuracy|case|coverage_gap",
      "claim": "一句话判断",
      "evidence": { "quote": "纠错稿摘句", "approx_time": "可选" },
      "verdict": "pass|issue|unverified",
      "confidence": "high|low",
      "remediation": "可选改法"
    }
  ]
}
```

## 硬约束

1. `verdict=issue` **必须**有非空 `evidence.quote`（来自纠错稿）；否则用 `unverified`。
2. `category=coverage_gap`（标题暗示但转写未讲到）→ **必须** `verdict=unverified`，改法写「对照讲义/回放确认」。
3. 标题只定主题范围，**不是**完整讲义；禁止用百科「应讲清单」扩大指控。
4. `anchor_strength=weak`（标题过泛如 day01）时：少下 `issue`，多 `unverified` / `pass`。
5. 对事不对人；不点名；完整句子。
6. 拿不准就 `unverified` + `confidence=low`。
