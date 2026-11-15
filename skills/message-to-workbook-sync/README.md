# 消息到报表同步（`message-to-workbook-sync`）

解析多种格式的半结构化通道消息，把归一后的值按单元格幂等写入已有报表，且不改变报表结构。

> 实现状态：通用运行时（读取、去重、写入、通知）已实现；语义归一、别名映射、归属优先级、多轮轮询仍是目标设计。详见 [能力矩阵](../../docs/capability-matrix.md)。

接入向导由仓库根目录的 `docs/onboarding-contract.md` 统一定义，拿不准就用快速开始预设。根目录的 `build.py` 可把本包生成成可独立分发的副本到 `dist/`。

## 适用场景

- 记录以文本模板或卡片消息发布，需要落到一份已存在的报表里。
- 报表版式归别人维护，公式、缓存值和其他 sheet 必须逐字节保留。
- 更正要覆盖旧值，包括针对已关闭的早期周期的更正。
- 一个周期跑多轮，最后一轮产出分组汇总。
- 实体与分组的归属必须权威，且绝不跨组泄漏。

## 不适用场景

追加式记录归集（`document-intake-ledger`）、可以直接用结构化表单代替消息解析的场景、需要新建报表文件的场景，以及结果需要审批闸门（`verified-batch-calculation`）的场景。

## 快速开始

自包含，仅依赖 Python 3.9+ 标准库，无需安装、无需凭证。

```bash
python3 run.py demo      # 内置样例数据，跑通全链路，产物在 demo-out/
python3 run.py setup     # 九步向导 -> config.json
python3 run.py doctor    # 校验配置与适配器
python3 run.py run       # 默认 dry-run；--no-dry-run 才真正写入
```

`setup --yes` 可无提示套用推荐预设；`python3 run.py install --apply` 把技能装进本地技能目录。向导契约见根目录 `docs/onboarding-contract.md`，逐字段说明见 `config.schema.md`。

## 接下来读什么

`DESIGN.md` 覆盖归属优先级、字段名与数值粘连的拆分、部件级外科写入、跨周期更正与失败矩阵。选电子表格库之前先读写策略：用错模式做一次全量保存，可能丢掉公式和自定义部件。字段说明在 `config.schema.md`。

## 文件清单

`SKILL.md`（契约）、`README.md`、`DESIGN.md`、`config.example.json`、`config.schema.md`。
