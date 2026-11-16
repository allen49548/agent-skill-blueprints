# Agent Skill Blueprints

四个**自包含、零依赖、可直接运行**的能力技能。clone 下来，跑一条命令，回答一遍向导，就能用——无需安装依赖、无需凭证、无需为每个用户改代码，也不绑定任何厂商 SDK。

仅依赖 Python 3.9+ 标准库，当前版本 **0.2.1**（[更新日志](CHANGELOG.md)）。

## 快速开始

```bash
git clone git@github.com:allen49548/agent-skill-blueprints.git
cd agent-skill-blueprints/skills/document-intake-ledger

python3 run.py demo      # 零配置，内置样例数据跑通全链路
python3 run.py setup     # 九步向导 -> config.json
python3 run.py doctor    # 校验配置与适配器
python3 run.py run       # 默认 dry-run，--no-dry-run 才真正写入
```

`demo` 就是「能跑」的证明；`setup --yes` 无提示套用推荐预设；`install --apply` 装进本地技能目录。把目录名换成另外三个包中的任意一个，命令完全一样。

## 四个技能

| 包 | 一句话 | 什么时候别用 |
| --- | --- | --- |
| [scheduled-digest-publisher](skills/scheduled-digest-publisher/) | 多源汇总成周期简报，突出关注实体，只投递一次 | 实时推送、一次性导出 |
| [verified-batch-calculation](skills/verified-batch-calculation/) | 按实体计算、独立复核、过审批闸门后投递 | 低风险单次计算 |
| [message-to-workbook-sync](skills/message-to-workbook-sync/) | 解析半结构化消息，按单元格写入已有报表 | 能直接用结构化表单 |
| [document-intake-ledger](skills/document-intake-ledger/) | 从文档抽记录、台账去重、追加明细行 | 可信 API 已保证恰好一次 |

每个包都能单独拷走运行；根目录 `build.py` 生成可独立分发的 `dist/`。

## 先说清楚：哪些是真的能跑的

共享运行时**已实现且有测试**，四个技能的「专属能力机制」是**目标设计**。`profile.json` 改的是默认值，不是算法。依赖任何不变量之前先读 [能力矩阵](docs/capability-matrix.md)。

| 范围 | 状态 |
| --- | --- |
| demo / setup / doctor / run / info / install / build | 已实现并有测试 |
| 本地目录、JSON、webhook 输入；CSV、JSON、XLSX 输出 | 已实现并有测试 |
| 四套通知模板；业务键去重台账；dry-run、备份、字节一致校验 | 已实现并有测试 |
| 飞书 / 企业微信 的群组列举与消息收发 | 仅契约，需项目提供适配器 |
| 安装定时任务 | 只写配置，不装调度 |
| 独立重算与审批、图像识别、语义归一、时区排序 | 目标设计，**未实现** |

这是可扩展的运行骨架，不是四个成品。

## 为什么没有学习成本

所有差异都落在向导生成的 `config.json` 里，代码对每个人完全一样；输入 / 输出 / 通知都是适配器，内置适配器零凭证可用，真实平台靠注册；`demo` 先跑通，`run` 默认 dry-run，`doctor` 说明问题；`setup` 可重跑，绝不从上一轮会话推断选择。

## 命令

| 命令 | 作用 | 外部影响 |
| --- | --- | --- |
| `demo` | 内置样例跑全链路 | 只写本地产物 |
| `setup` | 九步向导生成 config.json | 无 |
| `doctor` | 校验配置、引用、适配器、时区 | 无 |
| `run` | 正式链路，默认 dry-run | 只写变更清单 |
| `run --no-dry-run` | 允许真实写入与发送 | 仅限已配置适配器 |
| `info` | 显示 profile 与配置状态 | 无 |
| `install --apply` | 复制到本地技能目录 | 本地复制 |

向导契约见 [docs/onboarding-contract.md](docs/onboarding-contract.md)。

## 设计原则

按机制命名不按业务；配置优于常量；不变量是一等公民；默认幂等（重复由业务键判定，绝不靠金额相等）；不可逆动作有人把关、默认 dry-run；绝不改动源材料（外科式写入，先备份后校验）；失败必须可见。代码与概念用英文，面向人的 README 用中文。统一术语见 [docs/vocabulary.md](docs/vocabulary.md)。

## 开发与发布

```bash
python3 -m unittest discover -s tests -v   # 22 个测试
python3 tools/check_repo.py                # 编码、隐私、结构门禁
python3 build.py && python3 build.py --check
```

CI 在 Python 3.9–3.13 上跑测试、四个 demo、构建和门禁。改运行时先读 [CONTRIBUTING.md](CONTRIBUTING.md)：`skillkit/engine.py` 只有一份，四个 `run.py` 都是 shim。发布前跑门禁和测试，实现状态有变化就同步更新 `docs/capability-matrix.md` 和 `CHANGELOG.md`，完整流程见 [PUBLISHING.md](PUBLISHING.md)。

## 刻意不做什么

不接真实平台 API（`feishu` / `wecom` 只是配置可选值）；不自动装调度；不实现四个技能的专属机制；不收录真实姓名、账号标识、机器绝对路径、金额、截图、数据库状态，以及组织特有的奖惩 / 话术规则。

## 许可

MIT，见 [LICENSE](LICENSE)。
