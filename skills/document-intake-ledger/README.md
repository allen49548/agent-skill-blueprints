# 文档归集台账（`document-intake-ledger`）

从通道里的文档抽取结构化记录，按发送者归属，并通过分层台账保证同一件真实事项只被计入一次。

> 实现状态：通用运行时（读取、去重、写入、通知）已实现；图像识别、四层去重的前三层、状态机与确认任务仍是目标设计。详见 [能力矩阵](../../docs/capability-matrix.md)。

接入向导由仓库根目录的 `docs/onboarding-contract.md` 统一定义，拿不准就用快速开始预设。根目录的 `build.py` 可把本包生成成可独立分发的副本到 `dist/`。

## 适用场景

- 文档或截图来自多个发送者，重复提交很常见。
- 命中重复时必须说明原登记时间与当前状态，绝不能静默跳过。
- 目标报表不存在时，记录仍要留在台账里。
- 下游确认需要区分「可编辑」与「仅可查看」两种角色。
- 每一轮都要通报，包括完全没有变化的一轮。

## 不适用场景

固定版式的单元格更新（`message-to-workbook-sync`）、需要审批闸门的计算结果（`verified-batch-calculation`）、已保证恰好一次的可信 API，以及任何需要原地修改文档的流程。

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

`DESIGN.md` 定义四层去重、台账结构、状态机、追加式写入与失败矩阵。先读去重那一节：感知哈希命中但业务键不同属于误报，否则会把合法的不同记录丢掉。字段说明在 `config.schema.md`。

## 文件清单

`SKILL.md`（契约）、`README.md`、`DESIGN.md`、`config.example.json`、`config.schema.md`。
