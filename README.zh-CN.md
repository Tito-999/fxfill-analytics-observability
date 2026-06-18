[English](./README.md) | **简体中文** <!-- sync:language -->

# FxFill 数据分析与 AI Agent 可观测性平台

一个基于证据的数据分析工程与 AI Agent 可观测性平台，使用 Python、DuckDB、dbt、Streamlit 构建，并配备机器可验证的数据质量门禁。

> **Portfolio 范围：** 本仓库中所有产品、用户、Agent 和财务数据均为合成数据。本项目为本地参考实现，并非已部署的银行或生产级 SaaS 系统。

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![DuckDB](https://img.shields.io/badge/DuckDB-0.10-yellow.svg)](https://duckdb.org/)
[![dbt](https://img.shields.io/badge/dbt-core-1.8-orange.svg)](https://docs.getdbt.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.31-red.svg)](https://streamlit.io/)
[![406 Tests](https://img.shields.io/badge/Tests-406%20%2F%20406%20passed-brightgreen.svg)](https://github.com/Tito-999/fxfill-analytics-observability)
[![dbt Models](https://img.shields.io/badge/dbt%20Models-41%20%2F%2041-brightgreen.svg)](https://github.com/Tito-999/fxfill-analytics-observability)
[![dbt Tests](https://img.shields.io/badge/dbt%20Tests-44%20%2F%2044-brightgreen.svg)](https://github.com/Tito-999/fxfill-analytics-observability)
[![Release](https://img.shields.io/badge/Release-portfolio--v1.2.12-blue.svg)](https://github.com/Tito-999/fxfill-analytics-observability/releases/tag/portfolio-v1.2.12)
[![Synthetic Data](https://img.shields.io/badge/Data-Synthetic-lightgrey.svg)](https://github.com/Tito-999/fxfill-analytics-observability)

---

## 概览

FxFill Analytics 是一个完整的数据分析工程参考实现，模拟了一款帮助用户完成跨境汇款表单填写的 AI Agent 产品。该平台覆盖了从合成数据生成到维度建模、商业智能仪表板以及实验驱动决策的完整流程。

本项目展示了六大集成能力层：**产品分析**（转化漏斗、激活、留存队列、功能采用）、**数据分析工程**（DuckDB + dbt staging/intermediate/mart 层，共 41 个模型和 44 个数据测试）、**AI Agent 可观测性**（成功率、延迟百分位数、Token 使用量、成本、模型分布和错误类别）、**仪表板真实性**（跨层 UI 到数据库的指标核对，含 NaN/None 防护和 Plotly 轨迹检查）、**数据质量**（溯源检查、严格的行级核对、存储通过标志的重新计算以及过期制品检测）以及**基于证据的发布验证**（11 个必检门禁，采用 PASS/FAIL/NOT_RUN 语义，由 SHA-256 哈希的 dbt 制品和不可变 Git 标签支撑）。

---

## 快速开始

**Windows PowerShell:**

```powershell
git clone https://github.com/Tito-999/fxfill-analytics-observability.git
cd fxfill-analytics-observability

conda create -n fxfill_analytics python=3.11 -y
conda activate fxfill_analytics

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pip install -e .

# dbt profiles.yml is gitignored; create it before verification
@'
fxfill_analytics:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: "{{ env_var('FXFILL_DUCKDB_PATH', '../../warehouse/fxfill.duckdb') }}"
      schema: main
      threads: 4
'@ | Out-File -Encoding utf8 dbt_fxfill/profiles.yml

$env:PYTHONNOUSERSITE = "1"
$env:NO_PROXY = "127.0.0.1,localhost"

python scripts\verify_core_release.py
```

预期结果：

- 核心验收：`true`
- 必检发布门禁：11 / 11 `PASS`
- pytest：406 / 406 通过
- dbt 模型：41 / 41 成功执行
- dbt 测试：44 / 44 通过

> 不可变的 portfolio-v1.2.12 基线记录在[发布证据](reports/portfolio/releases/portfolio-v1.2.12/)中。当前 master 分支还包含已验证的 Windows 干净克隆可移植性修复。

---

## 架构

![架构图](docs/portfolio/architecture.png)

数据管道经历以下阶段：

**合成产品事件**
&rarr; **Parquet 数据**
&rarr; **DuckDB 数据仓库**
&rarr; **dbt Staging / Intermediate / Marts**
&rarr; **产品分析与 Agent 可观测性**
&rarr; **Streamlit / Plotly 仪表板**
&rarr; **仪表板真实性与严格核对**
&rarr; **基于证据的发布门禁**
&rarr; **不可变 Git 发布**

![阶段图](docs/portfolio/stages.png)

更多架构图可在 `docs/portfolio/` 中查看：

1. **architecture.png** 从数据生成到仪表板和实验分析的端到端管道
2. **data_flow.png** 数据模型层详情与转换依赖关系
3. **experiment_flow.png** 从假设到决策的 A/B 测试流程

---

## 核心能力

### 产品分析

转化漏斗分析、激活跟踪、每周留存队列、功能采用趋势、导出与放弃指标、基于 Bootstrap 置信区间的 A/B 实验评估以及 Kitagawa 根因分解。

### AI Agent 可观测性

Agent 运行量、成功率和错误率、P50/P95 延迟、Token 消耗量、单次任务成本、模型分布、错误类别分解以及涵盖四个监控仪表板区域的日期筛选运维视图。

### 数据分析工程

DuckDB 数据仓库配合 dbt staging（7 个模型）、intermediate（13 个模型）和 mart（21 个模型）层，共 41 个模型。21 个通用数据测试和 23 个单一测试确保了引用完整性、唯一性、非空约束和可接受值校验。

### 仪表板真实性

跨页面的自动化数据库到 UI 指标核对、零违规的日期筛选验证、NaN/None 渲染检查、留存成熟度合约验证以及实际的 Plotly 轨迹和点检查（检查了 3 张图中 12 条轨迹上的 136 个绘制数据点）。

### 数据质量

溯源检查确认 manifest 和 warehouse 之间的 run ID 一致，严格的行级 raw-to-staging 核对（7 张表，零差异），有限值检查，存储通过标志的重新计算以及过期制品检测。

### 发布验证

11 个必检发布门禁，采用 PASS/FAIL/NOT_RUN 语义，dbt 模型和测试制品经确认以不同哈希路径分离存储，SHA-256 证据链，Git-tree 候选审计以及带注释的不可变发布标签。

---

## 仪表板页面

![仪表板总览图](docs/portfolio/dashboard_contact_sheet.png)

| 页面 | 描述 |
|------|-------------|
| **首页** | 平台概览、关键指标和导航 |
| **高管概览** | 每日记分卡、每周业务回顾、高级 KPI |
| **转化漏斗** | 用户从注册、上传、自动填表到导出的完整旅程 |
| **留存与队列** | 每周留存队列和用户生命周期分析 |
| **功能采用** | 功能级使用趋势和采用率 |
| **Agent 可观测性** | Agent 运行轨迹、Token 使用量、成本、错误率和延迟 |
| **A/B 测试分析** | 含 Bootstrap 置信区间和细分效应的实验结果 |
| **根因分析** | 使用 Kitagawa 方法进行导出率分解 |
| **数据质量** | 核对、溯源和数据质量检查结果 |

---

## 项目规模

| 指标 | 数量 |
|---|---:|
| 源表 | 7 |
| dbt 模型 | 41 |
| Staging | 7 |
| Intermediate | 13 |
| Marts | 21 |
| 通用 dbt 测试 | 21 |
| 单一 dbt 测试 | 23 |
| dbt 测试总计 | 44 / 44 通过 |
| SQL 分析查询 | 20 |
| Streamlit 页面 | 8（1 个首页 + 7 个业务页面） |
| 图表 | ~30 |
| Bootstrap 迭代次数 | 5,000 |
| 自动化 pytest 测试 | 406 / 406 通过 |
| 必检发布门禁 | 11 / 11 PASS |
| 最新已验证发布 | `portfolio-v1.2.12` |

---

## 分析案例研究

### 根因：导出率分解

研究了一次模拟的表单导出率下降，使用 Kitagawa 分解方法将整体变化分解为比率效应和混合效应。分析定位了哪些用户细分群体导致了下降，以及根本原因是行为性的（细分群体内转化率降低）还是构成性的（向低转化率细分群体的偏移）。分解达到了小于 1e-9 的残差，证实了内部一致性。

### A/B 测试：validation_before_autofill_v1

评估了一项在表单自动填表前引入验证步骤的实验。分析流程应用了：

- 整体和细分层面的样本比率不匹配（SRM）检查
- 5,000 次迭代的 Bootstrap 重采样以获得稳健的置信区间
- 跨用户队列的细分层面效应分析

第 4 阶段实验决策为 **SHIP**，表明该功能展示了统计上显著的改进，效果量为正向。

---

## 工程质量

- **pytest：** 406 / 406 通过，0 失败、错误或跳过。
- **dbt 模型：** 41 / 41 成功执行。
- **dbt 测试：** 44 / 44 通过，包括 21 个通用测试和 23 个单一测试。
- **发布门禁：** 11 / 11 必检门禁报告 `PASS`。
- **代码质量：** Ruff 和 Black 通过；修改后的验证模块在隔离的 Python 3.11 环境中同样通过 mypy。
- **依赖完整性：** 在隔离环境中 `pip check` 报告 0 冲突。
- **仪表板冒烟测试：** HTTP 健康检查和首页端点返回 200，进程终止和端口释放均正常。
- **公开审计：** 0 个高危和 0 个中危发现。

发布验证器基于测量证据得出验收结论。缺失的检查保持 `NOT_RUN`；告警、失败的门禁、不完整的测量结果或不一致的存储/重新计算结果均会阻止验收通过。

---

## 已验证的发布证据

最新已验证发布为 [`portfolio-v1.2.12`](https://github.com/Tito-999/fxfill-analytics-observability/releases/tag/portfolio-v1.2.12)。

- 代码提交：`e1d54a10d28e33c66efabc69f44b76cf57e32fa9`
- 证据/master 提交：`839a910cf6b69f3f130ef2d3478da9d3bd745428`
- 核心验收：`true`
- 必检门禁：11 / 11 `PASS`
- pytest：406 / 406 通过
- dbt 模型：41 / 41 成功执行
- dbt 测试：44 / 44 通过

发布证据文件：

- [核心发布验收](reports/portfolio/releases/portfolio-v1.2.12/core_release_acceptance.json)
- [数据质量快照](reports/portfolio/releases/portfolio-v1.2.12/data_quality_snapshot.json)
- [仪表板真实性](reports/portfolio/releases/portfolio-v1.2.12/dashboard_truthfulness.json)
- [业务指标完整性](reports/portfolio/releases/portfolio-v1.2.12/business_metric_integrity.json)
- [机器摘要](reports/portfolio/releases/portfolio-v1.2.12/p2_8_4_machine_summary.json)
- [发布包清单](reports/portfolio/releases/portfolio-v1.2.12/release_bundle_manifest.json)

---

## 仓库结构

```
fxfill-analytics-observability/
data/                    # Generated synthetic data (Parquet/CSV)
dbt_fxfill/              # dbt models and configurations
models/
staging/         # 7 staging models
intermediate/    # 13 intermediate models
marts/           # 21 analytics marts
tests/               # 21 generic + 23 singular dbt tests
docs/
portfolio/           # Architecture diagrams and screenshots
scripts/                 # Pipeline automation and verification scripts
sql/                     # 20 SQL analysis queries
dashboard/               # 8-page Streamlit dashboard
tests/                   # 406-test automated verification suite
src/
fxfill_analytics/
verification/    # Release verifier and artifact validators
reports/
portfolio/
releases/
portfolio-v1.2.12/  # Machine-verified release evidence
requirements.txt
requirements-dev.txt
README.md
```

---

## 发布

最新已验证发布：

- [`portfolio-v1.2.12`](https://github.com/Tito-999/fxfill-analytics-observability/releases/tag/portfolio-v1.2.12)

更早的标签作为不可变历史检查点保留。

---

## 本项目展示内容

产品分析、数据分析工程、BI 工程、AI 产品分析、Agent 可观测性、数据质量工程以及基于证据的发布验证，在一个自包含、可本地复现的参考实现中。

---

## 局限性

- **仅合成数据** 所有行为和运营数据均为程序化生成
- **Portfolio/参考实现** 并非已部署的银行或生产级 SaaS 系统
- **无真实客户 PII** 所有用户身份和交易记录均为合成数据
- **无生产级银行交易** 财务数字为说明性场景假设
- **无云部署** 在 DuckDB 上本地运行；无流式数据接入
- **基于本地 DuckDB 的分析技术栈** 未针对分布式或高并发工作负载进行基准测试
- **Agent 遥测为模拟数据** 轨迹、Span 和成本数字均为生成数据，并非从实时 AI 服务采集

---

## 作者

由 Chengren Pang 设计与构建。

开发工作流包含自动化验证。

---

## 许可证

MIT 许可证 — 参见 [LICENSE](./LICENSE)。
