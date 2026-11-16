# 消息到报表同步（`message-to-workbook-sync`）

解析多种格式的半结构化通道消息，把归一后的值按单元格幂等写入已有报表，且不改变报表结构。

> 实现状态：通用运行时（读取 / 去重 / 写入 / 通知）已实现；语义归一、别名映射、归属优先级、多轮轮询仍是目标设计。见 [能力矩阵](../../docs/capability-matrix.md)。

## 适用 / 不适用

适用：
- 记录以文本模板或卡片消息发布，需要落到一份已存在的报表里
- 报表版式归别人维护，公式、缓存值和其他 sheet 必须逐字节保留
- 更正要覆盖旧值，包括已关闭的早期周期
- 一个周期跑多轮，最后一轮产出分组汇总；归属必须权威、绝不跨组泄漏

不适用：
- 追加式记录归集 → `document-intake-ledger`
- 能直接用结构化表单代替消息解析；需要新建报表文件
- 结果需要审批闸门 → `verified-batch-calculation`

## 快速开始

仅依赖 Python 3.9+ 标准库，无需安装、无需凭证。

```bash
python3 run.py demo      # 内置样例跑通全链路，产物在 demo-out/
python3 run.py setup     # 九步向导 -> config.json
python3 run.py doctor    # 校验配置与适配器
python3 run.py run       # 默认 dry-run；--no-dry-run 才真正写入
```

`setup --yes` 套用推荐预设；`install --apply` 装进本地技能目录。向导契约见根目录 `docs/onboarding-contract.md`，逐字段见 `config.schema.md`。

## 下一步读什么

`DESIGN.md` 覆盖归属优先级、字段与数值粘连拆分、部件级外科写入、跨周期更正与失败矩阵，选电子表格库前先读写策略：用错模式做一次全量保存可能丢掉公式和自定义部件。文件清单：`SKILL.md`（契约）、`README.md`、`DESIGN.md`、`config.example.json`、`config.schema.md`。
