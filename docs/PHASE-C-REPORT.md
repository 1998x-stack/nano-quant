# Phase C — 合成量化研究纵向闭环

状态：**待 CI 实测、待 PR 审核；不是 v1.0 正式发布**。

## 本次实现

- [Data] 版本化、确定性的三只虚构股票 OHLCV 数据，按合成工作日生成，所有数据带 UTC 时间戳和可用时间。
- [Finance] 复用 Decimal 会计、持仓市值和基础收益/回撤计算；完整财务理论工具库尚未实现。
- [Research] 使用 point-in-time close 计算 20 session 动量，预热不足明确拒绝。
- [Models] 无参数训练的动量基准，输出未校准排序分数；**不**宣称是未来收益或上涨概率的估计。
- [Strategies] 根据分数排序、固定 tie-break 选择最多两只股票。
- [Portfolio] 等权目标，在单标的上限和现金缓冲下转换为整数股交易意图。
- [Risk] 基础事前集中度、时间、资产池、超量卖出和重复订单审查；实际购买力在下一开盘再次校验。
- [Execution/Evaluation] 按固定合成月末收盘信号、下一合成工作日开盘成交、收盘盯市的日频事件循环。支持买卖、费用、滑点、现金与持仓账本、交易日志、NAV、总收益及最大回撤。

## 运行

```bash
python -m pip install -e ".[dev]"
python -m pytest -q --cov=nano_quant --cov-report=term-missing --cov-fail-under=85
python -m nano_quant.cli smoke --config examples/phase_b_golden.json
python -m nano_quant.cli backtest --config examples/daily_equity_v1.json --output-dir reports/daily_equity_v1
```

输出：`run-manifest.json`、`metrics.json`、`equity-curve.csv`、`trade-ledger.csv`、`rejections.csv`。相同配置和数据生成版本应有相同 run ID、交易账本与估值结果。报告中包含源代码版本（可用时）、合成数据 SHA256、代码包版本与核心假设。

## 重要限制

1. 数据为**合成示例**，不是经真实交易所验证的可交易市场数据，不可用以证明策略存在 Alpha。
2. 合成工作日**不模拟节假日或 DST**，固定 UTC 14:30 开盘、21:00 收盘及 21:01 数据可用。
3. 动量模型无参数拟合，仅构成可复现的排序基准。无统计训练/测试交叉验证、多重检验或真实样本外收益证据。
4. 仅支持 USD、整数股、无杠杆多头、固定费用/滑点、完全成交或因资金不足拒绝的模拟场景；不支持部分成交、分红、拆股、退市或复杂日内订单。
5. 报告采用初始现金不计息的现金基准。费用已记账；无高级 VaR、组合优化或市场容量估计。
6. 这条闭环不代表 v1.0 已通过全部 T01–T18 验收或拥有实盘能力。

## 验收

CI 需要执行 Ruff、mypy、pytest 覆盖率、Phase B 账本回归、Phase C CLI 完整报告生成。任何失败均不能合并为稳定版。

实际测试结果待 CI 完成后补充，禁止使用预期收益代替观测记录。
