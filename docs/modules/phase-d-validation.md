# Phase D API：证据、时间隔离与诊断

这些工具**已经实现**，但只用虚构数据验证；并非真实证券收益预测。

| API | 输入 → 输出 | 重要边界 |
| --- | --- | --- |
| `vintage_as_of` | `Observation` 序列 + UTC as_of → 当时已知的最新原始披露修订 | `operational_replay=True` 还检查实际摄取时间；不存在未来回填 |
| `historical_members` | `ListingRecord` + 日期 → 历史存续证券集合 | 缺少公告时间 known_at，不能单凭这个做到严谨真实 PIT |
| `reject_unsupported_actions` | 公司行为 + 日期范围 → 拒绝或通过 | 仍不支持分红/拆股/退市的资金账本 |
| `walk_forward_windows` | 交易日索引、训练/测试宽度、标签区间 → 带完整标签间隔的窗口 | 只是划分**方案**，没有模型训练/held-out 评估 |
| `rank_ic` | 对齐的因子与标签 → Spearman 秩相关 | 要求非恒定有限数据；不能证明因果 |
| `circular_shift_negative_control` | 因子、已实现收益、horizon、固定随机种子 → 诊断分布与 one-sided empirical p | 金融序列常不平稳，不能当成确认性显著性 |
| `order_fingerprint` | `OrderIntent` → SHA256 | 对齐批准和执行条款，但**不签名或授权用户身份** |
| `validation_audit` | 合成回测配置 → 诊断 JSON | 先比对订单路径再评价费用；禁止宣称实证 Alpha |

完整命令：

```bash
python -m nano_quant.cli validate \
  --config examples/daily_equity_v1.json \
  --output reports/validation/audit.json
```

审计报告有 `walk_forward_protocol_only`、`diagnostic_rank_ic`、`circular_shift_null_p_positive`、`cost_sensitivity`、`limitations`；明确无训练模型，且无真实样本外结论。
