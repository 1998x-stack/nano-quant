# Phase D — Independent Research Validation

状态：**开发工作分支已通过 CI；尚未合并或发布 v1.0**。

## 交付

- `data.evidence`：完整原始证据 SHA256、财报发布/可用/摄取时间、历史修订版本；禁止用未来修订结果回填历史。
- `ListingRecord`：重建历史证券存续范围，包含后续退市的虚构证券。
- `CorporateAction`：不支持分红、拆股、退市时显式拒绝，不能悄悄忽略。
- `validation.research`：有标签 horizon 间隔的 Walk-forward 窗口、Rank IC 和循环移位负向对照。
- `risk` + `execution`：风险审批绑定具体订单的 SHA256 指纹，修改数量/方向/参考价格上下文后拒绝原批准。
- `validation.audit`：对合成市场运行研究诊断、独立费用压力复跑，并生成 `audit.json`。

## 实际验证证据

[GitHub Actions workflow](https://github.com/1998x-stack/nano-quant/actions/runs/40483350598)，commit `26fba7f0`：
- Python 3.11、3.12 安装、Ruff、mypy、pytest、Phase B/Phase C 回归和 Phase D 审计全部成功。
- **109 passed，94.83% 行覆盖率**（Python 3.11）。
- 本次模拟费用压力审核日志为 `PASS`，且代码先对比订单成交路径，若不同则明确返回 `INCOMPARABLE_DIFFERENT_TRADE_PATH`。
- 后续改动必须以其最新 GitHub CI 结果为准。

## 本地执行

```bash
python -m pip install -e ".[dev]"
python -m pytest -q --cov=nano_quant --cov-report=term-missing --cov-fail-under=85
python -m nano_quant.cli backtest --config examples/daily_equity_v1.json --output-dir reports/daily
python -m nano_quant.cli validate --config examples/daily_equity_v1.json --output reports/validation/audit.json
```

输出的审计 JSON 明确设置 `trained_model=false`、`out_of_sample_model_results=false`。Walk-forward 只是**拟执行的分折协议**，没有真实模型训练与样本外绩效。循环移位仅为探索性诊断，不保证满足平稳性、独立性或多重检验条件。

## 真实研究未完成

**当前仍然仅是合成数据工程验证，不是机构级实证投资策略验证。**

尚未获取正式授权的交易所/财报数据，没有披露 `known_at` 的真实退市证券池，没有处理公司行为的账本会计，也没有真实市场上的样本外训练、交易冲击或 Alpha 证明。指纹不是身份签名或安全授权，不能用作真实券商权限。

本阶段 PR 需在 Phase B PR #2、Phase C PR #3 依次审核合并后再调整目标到 `main` 并完整复验，禁止绕过版本治理。
