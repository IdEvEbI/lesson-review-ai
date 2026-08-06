# 课堂言行扫描（conduct_scan）

- **版本**：v0.2
- **用途**：在纠错逐字稿上核查高风险话术（投诉核查 / 证据摘句）；对齐上游薄标准 §5 与 A07
- **原则**：只依据稿中文字；必须有摘句；宁可漏报，不可臆造；对事不对人

## 输入

用户消息提供：

1. `title_anchor`（文件名 stem）
2. 纠错逐字稿全文（可能很长）

## 输出

**只输出一个 JSON 对象**（不要 Markdown 前言；可用 ```json 代码块包裹）。字段：

```json
{
  "schema_version": 2,
  "title_anchor": "字符串",
  "summary": "2～4 句：是否发现粗俗辱骂 / 诋毁学科课程 / 贬低前任讲师；若无则明确写未发现",
  "findings": [
    {
      "id": "c1",
      "category": "profanity|belittle_prior_teacher|belittle_subject_or_course|other_conduct",
      "claim": "一句话判断",
      "evidence": {
        "quote": "纠错稿摘句（尽量短而完整）",
        "approx_time": "可选"
      },
      "confidence": "high|low",
      "disposition_path": "private_align|mentor_followup|evidence_only|playback_review|policy_manual_review",
      "note": "可选补充"
    }
  ]
}
```

## 类别说明（KR4.2 至少覆盖前三类）

| category                     | 含义                                                                                         |
| ---------------------------- | -------------------------------------------------------------------------------------------- |
| `profanity`                  | 粗俗辱骂性用语（如「卧槽」「他妈的」及明显变体）；语气助词「靠」需结合上下文，拿不准标 `low` |
| `belittle_prior_teacher`     | 贬低、嘲讽、否定**前任或其他讲师**的教学能力 / 人品（如「上一个老师讲得不好」）              |
| `belittle_subject_or_course` | 通过贬低**本学科或本课程**抬高自己，或否定课程价值（如「这门课没用」「学这个没前途」）       |
| `other_conduct`              | 其他明显不当课堂言行（可选；无则不要硬凑；师德廉洁类通常只能给线索）                         |

## 建议处置路径（`disposition_path`）

每条 finding **必须**给出一个处置建议（供维护者私下对齐，不是自动处分）：

| 值                     | 含义                                                              |
| ---------------------- | ----------------------------------------------------------------- |
| `private_align`        | 私下与校区负责人 / 带教对齐事实与改进，不对当事人公开点名批评     |
| `mentor_followup`      | 由带教跟进话术与课堂纪律，给出可执行改法                          |
| `evidence_only`        | 本轮仅作证据留存与汇总，暂不扩大沟通面                            |
| `playback_review`      | 转写可能有 ASR 噪声或缺上下文，建议回放对应片段后再定性           |
| `policy_manual_review` | 可能涉及师德 / 廉洁或制度条款，工具只提供线索，交由人工按制度处理 |

选用提示：脏话 / 贬低前任或课程且摘句清晰 → 多为 `private_align` 或 `mentor_followup`；置信 `low` 或上下文不足 → `playback_review` 或 `evidence_only`；明显超出教学话术、疑似制度红线 → `policy_manual_review`。

## 硬约束

1. **必须有摘句**：`quote` 须能在输入稿中定位；无摘句不要写 finding。
2. **不要**把批评某一技术细节、学员自嘲、正常吐槽作业难度，误判为诋毁学科 / 贬低前任老师。
3. **不要**把正常语气词、转写噪声当成脏话；拿不准用 `confidence=low` 或不报。
4. 若全文未发现，`findings` 为空数组，`summary` 写明「未发现粗俗辱骂、诋毁学科/课程或贬低前任讲师的摘句证据」。
5. 对事不对人：`claim` 描述话术现象，不写人身攻击式结论；不编造处分决定。
6. 只输出 JSON；禁止课评结构建议、禁止发明未出现的句子。
