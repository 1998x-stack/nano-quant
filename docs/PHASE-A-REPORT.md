# Phase A — 架构基线交付与后续交接

日期：2026-10-27。状态：文档审查中（未作为 v1.0 发布）。

## 仓库现状与实作边界

Phase A 开始时，远程仓库为空、无历史源代码和已有分支。为使 GitHub 上的工作可以被审查，先在 `main` 放入最小 README 创建根提交，然后从该提交创建 `docs/phase-a-architecture` 工作分支。此阶段没有实现可运行的量化引擎、Python 包、CI 或测试。

## 本阶段决策

1. 一个 Python package + 一个 Git 仓库；八大领域由长期目录维护，模块开发分支为短期协作单位。
2. main 为已审查稳定集成；发布分支稳定化，正式标签为不可变版本锚点。
3. v1.0 标准问题限制为 USD、日频股票、多头无杠杆，先用合成 fixture 打通链路。
4. T 收盘产生信号，T+1 开盘模拟成交，显式披露价格和手续费口径。
5. `available_at` + `as_of` 强制约束未来数据，真实运营重放还检查 `ingested_at`。
6. 研究正确、软件正确、交易账本正确和预测有效分开验收。
7. 只在有明确数据、效能或研究需求时扩展 v2.0 的模型/数据/组合能力。

## 文件导航

- [系统架构](architecture/overview.md)
- [接口契约](architecture/contracts.md)
- [PIT 规范](architecture/temporal-data.md)
- [ADR](architecture/adr/0001-modular-monolith.md)
- [证据链规则](research/evidence-policy.md)
- [Git/发布治理](governance/branching-and-releases.md)
- [版本实施计划](releases/v1.0-plan.md)
- [验收矩阵](validation/acceptance.md)

## 尚未完成与风险

- 代码和 API 仅处于设计状态，真实 Python 包结构、测试、CI 和报告未存在。
- 真正的数据供应商、使用许可和证券池需在真实历史研究前选择。
- v1.0 模型基准和命令行参数将在 Phase B 通过实现验证后冻结。
- branch protection 等仓库设置尚未配置；需在 Phase B 确认 GitHub 权限和检查名称。
- ADR 中的最低 Python/依赖版本需要通过 CI 矩阵与依赖兼容测试验证。

## Phase B 第一工作项

从 `main` 已审查状态创建 `feature/phase-b-scaffold` 或第一条短期模块分支，建立 `pyproject.toml`、`src/nano_quant/core`、基础类型/时间校验、synthetic fixture、测试及 CI。第一条可验证命令：干净环境安装 + `pytest` 通过；第一条纵向 smoke：用最少两个交易日的人工订单产生正确的成交、仓位和账本。

正式合并、发布和版本标签必须以真实自动化测试结果为依据。
