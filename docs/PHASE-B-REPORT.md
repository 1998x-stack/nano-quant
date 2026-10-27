# Phase B — 实现与验收报告

状态：**工程基座已通过自动化 CI，PR #2 待代码审核与合并**；完整 v1.0 尚未实现。

已核验 GitHub Actions：[PR #2](https://github.com/1998x-stack/nano-quant/pull/2) 的 [Python 3.11/3.12 CI 运行](https://github.com/1998x-stack/nano-quant/actions/runs/40472143078)。完成了可编辑安装、Ruff、mypy、pytest 与 CLI smoke：**42 tests passed，Python 3.11 行覆盖率 94.06%**。该证据对应 commit `e4e2e104`，后续纯文档提交也应由最新 CI 重新核验。

## 交付清单

- `pyproject.toml`：可安装包、Python 3.11+、开发依赖及命令行入口。
- `src/nano_quant/core`：核心时间、行情、快照、订单、审批、成交和账本状态类型。
- `src/nano_quant/data`：数据可得时间过滤、固定双日合成行情。
- `src/nano_quant/execution`：单标的 BUY 的确定性模拟账本、模拟审批校验、费用/滑点。
- `src/nano_quant/cli.py`：`smoke` 工作流，`backtest` 明确尚未实现。
- `examples/phase_b_golden.json`：严格 schema 的模拟场景。
- `tests/`：独立黄金数值案例、不可变数据契约、as-of 反事实和 CLI 配置测试。
- `.github/workflows/ci.yml`：Python 3.11/3.12 双版本安装、Ruff、mypy、pytest、CLI smoke。

## 实际执行命令

```bash
python -m pip install -e ".[dev]"
python -m ruff check .
python -m mypy src/nano_quant
python -m pytest -q --cov=nano_quant --cov-report=term-missing --cov-fail-under=85
python -m nano_quant.cli smoke --config examples/phase_b_golden.json
# 或安装后直接运行：
nano-quant smoke --config examples/phase_b_golden.json
```

## 期望 golden 结果

```text
fill_price:    10.01
fee_usd:       1.00
cash_usd:      898.90
position:      10 shares
nav_usd:       1008.90
pnl_usd:       8.90
```

## 尚未实现

真正的 20 日因子、模型训练、策略信号、目标组合生成、独立风险审核、多资产执行、回测净值序列和研究绩效评估。此文档不将合成行情输出解释为实际投资收益。

## Phase B 退出条件

工程自动化验收已通过；**PR 仍待审核合并**，因此尚未宣称 Phase B 已进入 main。只有审核完成、最新 HEAD 的必需 CI 检查通过且 PR 合并后，才可把 Phase B 标记为正式集成交付完成。若 CI 未运行或测试失败，必须如实列出失败项与修复状态。
