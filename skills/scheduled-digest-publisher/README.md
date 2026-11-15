# 周期性简报发布（`scheduled-digest-publisher`）

把多个来源汇总成按周期编号的一份简报，始终突出一个配置的关注实体，把所有时间统一到一个时区，并只投递一次到白名单通道。

> 实现状态：通用运行时（读取、去重、写入、通知）已实现；多源抓取、排名、关注实体、时区换算与焦点板块仍是目标设计。详见 [能力矩阵](../../docs/capability-matrix.md)。

接入向导由仓库根目录的 `docs/onboarding-contract.md` 统一定义，拿不准就用快速开始预设。根目录的 `build.py` 可把本包生成成可独立分发的副本到 `dist/`。

## 适用场景

- 定期简报、变更摘要、事件汇总或日程表需要按时发出。
- 来自异构来源的条目需要做时间窗过滤、去重和定量的精选。
- 某个配置的实体即使本周期没有相关事件，也必须出现在简报里。
- 运行必须可以安全重跑，也适合无人值守投递。

## 不适用场景

实时事件推送、对话式追问、一次性导出，以及投递前必须由人审批的内容（见 `verified-batch-calculation`）。

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

`DESIGN.md` 覆盖跨时区边界的采集窗口、幂等键、状态机与失败矩阵。选调度器之前先读它：幂等键里少了通道标识，会静默吞掉本该发出的消息。字段说明在 `config.schema.md`。

## 文件清单

`SKILL.md`（契约）、`README.md`、`DESIGN.md`、`config.example.json`、`config.schema.md`。
