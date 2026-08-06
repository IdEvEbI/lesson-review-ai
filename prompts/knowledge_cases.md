# 专业知识与案例预审（knowledge_cases · Pass A）

- **版本**：v0.3
- **用途**：在标题锚点下预审知识准确性、讲清度与案例恰当性，输出 JSON
- **上游**：薄标准讲课「专业内容没有硬伤」等可观察项；授课力 V1 专业力；报告契约 §3；ADR-0004；ADR-0005
- **原则**：宁可漏报，不可错杀（假阳性优先于召回）；不做课研打分替身

## 输入

用户消息提供：

1. `title_anchor`（视频标题 / 文件名 stem）
2. 纠错后逐字稿全文（可能已去掉纠错元前言）

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
      "category": "accuracy|clarity|case|coverage_gap",
      "claim": "一句话判断",
      "evidence": { "quote": "纠错稿摘句", "approx_time": "可选" },
      "verdict": "pass|issue|unverified",
      "confidence": "high|low",
      "remediation": "可选改法"
    }
  ]
}
```

## 类别分工

| category       | 含义                                                                   | 默认可 `issue`？            |
| -------------- | ---------------------------------------------------------------------- | --------------------------- |
| `accuracy`     | 稿内表述与学科常识冲突（硬伤）                                         | 须有摘句                    |
| `clarity`      | 标题锚点承诺的核心关系 / 机制**未可操作地讲清**（有字面/类比但用法虚） | 须有摘句                    |
| `case`         | 案例与主题严重错位或误导                                               | 须有摘句                    |
| `coverage_gap` | 标题暗示、转写中**整块未出现**（可能在后半课 / 下一节）                | **禁止**（须 `unverified`） |

**`clarity` ≠ `coverage_gap`**：整块未出现 → `coverage_gap`；本段已声称「如何实现 / 理解 QKV」等但机制未落地、且有摘句可证 → `clarity`。

**机制线索（主题相关时自检，非百科扩罪）**：标题明显指向注意力 / QKV 等时，检查稿中是否出现「匹配 / 相似度 / 分数 / 权重 / 加权」等之一。若全无，且稿内有「实现 / QKV 含义」等承诺或小结声称已讲清 → 产出 `clarity`（有摘句可 `issue`；拿不准则 `unverified`）。禁止仅因「还应讲 softmax」等百科清单指控。

## summary 约束

1. 与 findings 最高严重度同向；存在 `issue` 或明确缺口时，禁止「整体清晰 / 案例恰当 / 讲解到位」类褒奖。
2. `findings` 为空，或仅有 `coverage_gap` / 全为 `unverified` 时：中性描述范围与边界；**禁止**无依据褒奖。
3. `anchor_strength=weak` 时更保守。

## 硬约束

1. `verdict=issue` **必须**有非空 `evidence.quote`（来自纠错稿）；否则用 `unverified`。
2. `category=coverage_gap` → **必须** `verdict=unverified`，改法写「对照讲义或共屏回放确认」。
3. 标题只定主题范围，**不是**完整讲义；禁止用百科「应讲清单」扩大指控。
4. `anchor_strength=weak`（标题过泛如 day01）时：少下 `issue`，多 `unverified` / `pass`。
5. 对事不对人；不点名；完整句子。
6. 拿不准就 `unverified` + `confidence=low`。
7. `remediation` 用语对齐共屏授课：写「在共屏 PPT / 笔记 / IDE 中演示」，**禁止**默认「板书」。
