# Agent Skill Blueprints

四个**自包含、可直接运行**的能力技能。clone 下来，跑一条命令，回答一遍向导，就能用。无需安装依赖、无需凭证、无需为每个用户改代码，也不绑定任何厂商 SDK。

仅依赖 Python 3.9+ 标准库。当前版本 **0.2.1**（[更新日志](CHANGELOG.md)）。

## 快速开始

```bash
git clone git@github.com:allen49548/agent-skill-blueprints.git
cd agent-skill-blueprints/skills/document-intake-ledger

python3 run.py demo      # 零配置，内置样例数据，跑通全链路
python3 run.py setup     # 九步交互向导 -> config.json
python3 run.py doctor    # 校验配置、适配器和权限
python3 run.py run       # 默认 dry-run；--no-dry-run 才真正写入
```

`demo` 就是「能跑」的证明：读取内置记录、去重、写出 XLSX / CSV / JSON、渲染四套通知模板，并在 `demo-out/` 留下运行日志。不需要配置文件，也不需要联网。

`setup --yes` 可无提示套用推荐预设；`python3 run.py install --apply` 把技能装进 `~/.workbuddy/skills/<slug>/`，供 Agent 直接调用。把上面的目录名换成另外三个包中的任意一个，命令完全一样。

## 先看这里：哪些是真的能跑的

共享运行时是**已实现且有测试**的代码，但四个技能的「专属能力机制」目前是**目标设计**，不是实现。`profile.json` 改的是默认值，不是算法。在依赖任何不变量之前，请先读 [能力矩阵](docs/capability-matrix.md)。

| 范围 | 状态 |
| --- | --- |
| demo / setup / doctor / run / info / install / build | 已实现并有测试 |
| 本地目录、JSON、webhook 输入；CSV、JSON、XLSX 输出 | 已实现并有测试 |
| 四套通知模板；业务键去重台账 | 已实现并有测试 |
| dry-run、备份、未改动部件字节一致校验 | 已实现并有测试 |
| 飞书 / 企业微信 的群组列举与消息收发 | 仅契约，需要项目提供适配器 |
| 安装定时任务 | 仅写入配置，不会真的安装调度 |
| 独立重算与审批闸门、图像识别、语义归一、时区排序 | 目标设计，**未实现** |

这是一个可以扩展的运行骨架，不是四个成品。把话说清楚是刻意的。

## 为什么没有学习成本

| 顾虑 | 怎么处理 |
| --- | --- |
| 用户不同、数据不同 | 所有差异都在向导生成的 `config.json` 里，代码对每个人完全一样 |
| 平台不同 | 输入、输出、通知都是适配器。内置适配器（本地目录、CSV、JSON、XLSX、控制台）零凭证可用；真实平台靠注册，不写死 |
| 第一次不敢跑 | `demo` 用样例数据跑完整链路；`run` 默认 dry-run；`doctor` 会说明问题 |
| 想装成技能 | `install --apply` 直接复制到本地技能目录，不用手工接线 |
| 想改主意 | `setup` 可以重跑，绝不从上一轮会话里推断选择 |

## 四个技能

| 包 | 能力 | 什么时候用 | 什么时候别用 |
| --- | --- | --- | --- |
| [scheduled-digest-publisher](skills/scheduled-digest-publisher/) | 多源汇总成周期性简报，突出一个关注实体，统一时区，只投递一次 | 定期简报、状态汇总、变更摘要、日程推送 | 实时推送，或没有投递环节的一次性导出 |
| [verified-batch-calculation](skills/verified-batch-calculation/) | 按实体计算结果、独立复核、经审批闸门后逐人投递 | 结果代价高、规则因人而异、错数字绝不能发出去 | 可回滚的低风险单次计算 |
| [message-to-workbook-sync](skills/message-to-workbook-sync/) | 解析半结构化消息，把归一后的值按单元格写入已有报表 | 报表版式固定、不能改结构 | 表单归你自己，可以直接写结构化记录 |
| [document-intake-ledger](skills/document-intake-ledger/) | 从文档抽取记录、台账去重、追加明细行、驱动状态机 | 同一份材料可能重复提交，重复计数是主要风险 | 可信 API 已保证恰好一次 |

每个包都是独立的：把目录拷到任何地方都能跑。仓库根目录的 `build.py` 会生成可单独分发的副本到 `dist/`。

## 命令

| 命令 | 作用 | 外部影响 |
| --- | --- | --- |
| `demo` | 用内置样例数据跑完整链路 | 只写本地产物 |
| `setup` | 九步向导，生成 `config.json` | 无 |
| `doctor` | 校验配置、`*_ref` 引用、适配器、时区、dry-run 状态 | 无 |
| `run` | 正式链路，默认 dry-run | 只写变更清单 |
| `run --no-dry-run` | 允许真实写入与发送 | 仅限已配置适配器 |
| `info` | 显示 profile 与配置状态 | 无 |
| `install --apply` | 复制本技能到本地技能目录 | 本地复制 |

## 向导

九步：预设或自定义 → 平台 → 列出全部群组多选 → 消息来源类型 → 输出目标 → 通知模板 → 定时 → 全量回显确认 → 试跑。「新建报表」是唯一需要显式授权的动作。任何内容写入前，都会把所有选择回显一遍。

完整契约见 [docs/onboarding-contract.md](docs/onboarding-contract.md)。各包适用步骤不同，不适用的会说明原因后跳过，不会静默略过。

## 开发

```bash
python3 -m unittest discover -s tests -v   # 22 个测试，仅标准库
python3 tools/check_repo.py                # 编码、隐私、JSON、结构门禁
python3 build.py && python3 build.py --check   # 生成独立分发包到 dist/
```

每次 push 与 PR，CI 都会在 Python 3.9–3.13 上跑测试、四个 demo、构建和门禁。修改运行时前请读 [CONTRIBUTING.md](CONTRIBUTING.md)：`skillkit/engine.py` 只有一份，四个 `run.py` 都是 shim。要把单个技能分发到别处，跑 `build.py` 后复制 `dist/<slug>/`。

## 设计原则

1. **按机制命名，不按业务命名。** 标识符和概念里不出现业务角色、品牌名或项目名。
2. **配置优于常量。** 标识符、路径、阈值、时间都是配置字段，不写进代码。
3. **不变量是一等公民。** 每个包把「绝不能破的规则」和灵活流程分开写清楚。
4. **默认幂等。** 重跑安全；重复由业务键判定，绝不靠金额相等。
5. **不可逆动作要有人把关。** 审批、投递、真实写入都是显式步骤，默认 dry-run。
6. **绝不改动源材料。** 对已有文件的写入是外科式的，且先备份、后校验。
7. **失败必须可见。** 允许降级，不允许静默；每次跳过和失败都进运行日志。
8. **代码与概念用英文，面向人的 README 用中文。** 命名、配置键、设计文档和注释保持英文；README 面向使用者，用中文。

统一术语：`entity`、`channel`、`workbook`、`approver`、`recipient`、`source`、`run`、`ledger`。见 [docs/vocabulary.md](docs/vocabulary.md)。

## 仓库结构

```
agent-skill-blueprints/
|-- README.md  LICENSE  CHANGELOG.md  SECURITY.md  VERSION
|-- CONTRIBUTING.md  PUBLISHING.md  .gitignore
|-- build.py                     生成独立分发包到 dist/
|-- skillkit/
|   |-- __init__.py              __version__
|   `-- engine.py                唯一的运行时源码
|-- tools/check_repo.py          仓库门禁
|-- tests/                       标准库 unittest 套件
|-- .github/workflows/ci.yml      测试矩阵与门禁
|-- .github/ISSUE_TEMPLATE/
|-- docs/
|   |-- capability-matrix.md     已实现 / 目标设计对照（先读）
|   |-- onboarding-contract.md   共用的向导与边界
|   |-- abstraction-map.md       命名沿革与决策记录
|   `-- vocabulary.md
`-- skills/<slug>/
    |-- run.py                   薄 shim（四份相同）
    |-- profile.json             各技能默认值与适用步骤
    |-- SKILL.md  README.md  DESIGN.md
    |-- config.example.json  config.schema.md
    `-- examples/demo_input.json
```

`config.json`、`inbox/`、`out/`、`demo-out/`、`state/`、`dist/` 都是本地生成物，已 gitignore。

## 刻意不做什么

- 不接真实平台 API。`feishu` / `wecom` 只是配置可选值，网络调用是适配器插槽。
- 不自动装调度。`setup` 只把 cron 和时区写进配置，不会安装定时任务。
- 不实现四个技能的专属机制。见上方矩阵与 `docs/capability-matrix.md`。
- 不收录真实姓名、账号/会话标识、机器绝对路径、金额、截图和数据库状态。
- 不收录某个组织特有的奖惩、排名、话术规则。
- 不收录第三方市场技能和作者侧维护工具。

## 发布检查

公开推送前跑 `python3 tools/check_repo.py` 和 `python3 -m unittest discover -s tests`，CI 也会强制检查。若实现状态有变化，请在同一个 PR 里更新 `docs/capability-matrix.md` 和 `CHANGELOG.md`。完整的发布与隐私预检流程见 [PUBLISHING.md](PUBLISHING.md)。

## 许可

MIT，见 [LICENSE](LICENSE)。
