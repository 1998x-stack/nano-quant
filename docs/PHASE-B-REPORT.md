# Phase B — 实现与验收报告

状态：**开发分支的早期工程基座**；完整 v1.0 未实现。

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

只有在 GitHub CI 完成且所有必需检查通过、PR 被审核合入 main 之后，才可把 Phase B 标记为最终交付完成。若 CI 未运行或测试失败，必须如实列出失败项与修复状态。
