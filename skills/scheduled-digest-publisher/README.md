# 周期性简报发布（`scheduled-digest-publisher`）

把多个来源汇总成按周期编号的一份简报，始终突出一个配置的关注实体，统一时区，只投递一次到白名单通道。

> 实现状态：通用运行时（读取 / 去重 / 写入 / 通知）已实现；多源抓取、排名、关注实体、时区换算与焦点板块仍是目标设计。见 [能力矩阵](../../docs/capability-matrix.md)。

## 适用 / 不适用

适用：
- 定期简报、变更摘要、事件汇总或日程表需要按时发出
- 异构来源的条目需要时间窗过滤、去重和定量精选
- 关注的实体即使本周期没有相关事件，也必须出现在简报里
- 运行必须可安全重跑，也适合无人值守投递

不适用：
- 实时事件推送、对话式追问、一次性导出
- 投递前必须由人审批 → `verified-batch-calculation`

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

`DESIGN.md` 覆盖跨时区的采集窗口、幂等键、状态机与失败矩阵，选调度器前先读：幂等键里少了通道标识会静默吞掉该发的消息。文件清单：`SKILL.md`（契约）、`README.md`、`DESIGN.md`、`config.example.json`、`config.schema.md`。
