# 可复核批量计算（`verified-batch-calculation`）

按已确认的规则计算各实体的结果，通过独立路径复核，再经指纹绑定的审批闸门，逐人投递各自结果。业务能力恰好只有两个：`compute` 和 `verify`。

> **实现状态：目标设计，尚未实现。** 当前只运行通用流水线；独立重算、八类核对、审批闸门与指纹绑定都不在运行时里。依赖任何不变量之前，务必先读 [能力矩阵](../../docs/capability-matrix.md)。

## 适用 / 不适用

适用：
- 周期性分配、额度、评分或权益计算代价高，且规则因实体而异
- 规则从历史结果反推，必须由人确认后才能使用
- 错误结果绝不能投递，校验不能复用自己的计算实现
- 定时任务必须停在预览，等待审批人

不适用：
- 低风险、可回滚的单次计算
- 文档归集去重 → `document-intake-ledger`；固定版式报表更新 → `message-to-workbook-sync`
- 任何需要第三种业务能力的流水线

## 快速开始

仅依赖 Python 3.9+ 标准库，无需安装、无需凭证。注意：以下命令跑的是共享的通用流水线，不是上面描述的复核能力。

```bash
python3 run.py demo      # 内置样例跑通全链路，产物在 demo-out/
python3 run.py setup     # 九步向导 -> config.json
python3 run.py doctor    # 校验配置与适配器
python3 run.py run       # 默认 dry-run；--no-dry-run 才真正写入
```

`setup --yes` 套用推荐预设；`install --apply` 装进本地技能目录。向导契约见根目录 `docs/onboarding-contract.md`，逐字段见 `config.schema.md`。

## 下一步读什么

`DESIGN.md` 定义规则 DSL 安全约束、指纹、状态机与失败矩阵，属目标设计，先读指纹一节：确认未绑定输入、规则与结果就可能被复用到已变更的结果上。文件清单：`SKILL.md`（契约）、`README.md`、`DESIGN.md`、`config.example.json`、`config.schema.md`。
