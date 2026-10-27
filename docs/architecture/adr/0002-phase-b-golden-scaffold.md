# ADR-0002 — Phase B minimal synthetic gold test and JSON config

- 状态：Accepted for Phase B scaffold
- 日期：2026-10-27

## 决策

为了用最少第三方依赖建立可重复的工程验证，Phase B 只实现 `core` 的核心值对象、合成两日价格快照、模拟多头 BUY 账本和 CLI smoke。配置采用 JSON（标准库可严格解析），而不是 Phase A 拟议的 YAML（需要新增解析依赖）。完整 `backtest --config` 保留为 Phase C 的独立命令；在此之前会明确返回非零“尚未实现”。

账本演示仅允许 USD、整数股、单标的买入、给定 10bps 滑点与固定手续费；通过事先构造的**mock 风险审批**测试执行门禁，不将其误称为完整风控。

`PriceBar` 在 Phase A 契约之上增加 `open_at`，以区分“下一交易日开盘模拟成交”和“收盘行情事件可用”。`PortfolioState.nav` 由现金和持仓标记价计算，为只读派生属性，而非可与账本不一致的任意存储字段。

## 质量边界

- `data.snapshot` 用 `available_at <= as_of` 和 `event_at <= as_of` 构建时间快照。
- 账本只能使用下一次行情 `open` 成交，在该日收盘行情变为可用后记 `close` NAV。
- `RiskDecision` 是显式模拟对象；真实审批策略、长期订单生命周期、多资产、做空、公司行为及历史日历留待 Phase C/D。
- 交易费用计算采用 `Decimal` 和美分量化。
- 工程 CI 对 Python 3.11 与 3.12 执行安装、lint、typing、测试、smoke。

## 可检验后果

Golden Ledger A 应得到现金 $898.90，10 股，NAV $1008.90。T+1 行情价格扰动不改变 T 日快照。未经审批的订单被拒绝。重复成交同一订单被拒绝。以上必须由实际测试结果证明。

## 被拒绝的替代方案

直接生成复杂回测引擎或机器学习模型：既延误基础会计和时间正确性验证，又容易让测试与研究有效性混淆。
