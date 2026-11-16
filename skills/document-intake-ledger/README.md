# 文档归集台账（`document-intake-ledger`）

从通道文档抽取结构化记录，按发送者归属，用台账保证同一件真实事项只被计入一次。

> 实现状态：通用运行时（读取 / 去重 / 写入 / 通知）已实现；图像识别、四层去重的前三层、状态机与确认任务仍是目标设计。见 [能力矩阵](../../docs/capability-matrix.md)。

## 适用 / 不适用

适用：
- 文档或截图来自多个发送者，重复提交常见
- 命中重复时必须说明原登记时间与状态，不能静默跳过
- 目标报表不存在时，记录仍要留在台账里
- 每轮都要通报，包括完全没有变化的一轮

不适用：
- 固定版式单元格更新 → `message-to-workbook-sync`
- 需要审批闸门的计算结果 → `verified-batch-calculation`
- 可信 API 已保证恰好一次；需要原地修改文档的流程

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

`DESIGN.md` 定义四层去重、台账、状态机与追加式写入，先读去重一节：感知哈希命中但业务键不同属误报。文件清单：`SKILL.md`（契约）、`README.md`、`DESIGN.md`、`config.example.json`、`config.schema.md`。
