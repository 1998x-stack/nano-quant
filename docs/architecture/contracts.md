# 核心模块接口契约（Phase A，设计而非实现）

## 1. 全局约定

- Python 包名为 `nano_quant`，模块之间通过 `core` 的不可变值对象通信。公开 API 优先明确字段类型；禁止直接依赖其他模块的内部私有实现。
- `instrument_id` 采用稳定内部标识，不将可能复用的 ticker 当作唯一主键；ticker、交易场所、币种映射放在证券主数据中。
- 交易时点使用具备时区信息的 UTC `datetime`；`session_date` 是交易所本地交易日期；不允许 naive datetime。数值计算可用 float，但**现金、成交额、费用和账本持仓成本**采用 `Decimal` 或经验证的整数最小货币单位，避免浮点累计误差。
- 所有收益率明确写出周期、币种、含不含分红、简单/对数定义。目标 `horizon` 必须与标签的未来区间完全一致。
- `available_at` 表示信息可合理获取的时刻；`as_of` 是决策快照冻结时刻。任何输入必须满足 `available_at <= as_of`。
- 市场价格用于成交必须是**未复权可交易价格**；研究用总回报/复权系列与公司行为记录必须有明确转换和核对规则。v1.0 合成示例没有公司行为；真实适配器遇未受支持的公司行为应显式拒绝或标注不可用，而不是静默忽略。
- 日频标准事件顺序：T 收盘数据变为可用 → T 收盘后生成研究/预测/信号/目标 → 风控审核 → 最早在 T+1 开盘生成模拟成交 → T+1 收盘估值。不能使用 T+1 开盘价来构造 T 的信号。
- 不允许数据层因缺失日期自动向未来填补；指标预热不足时返回缺失状态，不得填入 0 伪装有效信号。

## 2. 公共对象（字段为最低契约）

| 对象 | 必要字段 | 关键不变量与用途 |
| --- | --- | --- |
| `PriceBar` | `instrument_id, session_date, open, high, low, close, volume, event_at, available_at, source_id` | OHLC 为非负且合理，成交量非负，带时区；价格原始口径明确 |
| `DataSnapshot` | `as_of, bars, universe, calendar_id, data_manifest_id` | 内部任何数据不可晚于 `as_of` 可得；确定股票池及退市处理规则 |
| `FactorFrame` | `as_of, factor_names, instrument_ids, values, lookback_spec, provenance` | 每个值对应的输入截止时间不晚于 `as_of` |
| `Forecast` | `as_of, horizon, target, estimates, model_version, training_cutoff` | 训练和特征截止时间均先于或等于决策时刻；声明单位与方向 |
| `StrategySignal` | `as_of, instrument_id, score, action, strategy_version, reason` | `action` 为枚举；无预测信息不允许伪造信号 |
| `TargetPortfolio` | `as_of, target_weights, base_currency, constraints_id` | 多头无杠杆：每只权重 >=0，总权重 <=1，余额留作现金 |
| `OrderIntent` | `order_id, instrument_id, side, quantity, created_at, earliest_execution_at, reference_price_context` | 数量 >0；`earliest_execution_at > created_at` 用于日频标准约定；订单 ID 唯一 |
| `RiskDecision` | `as_of, order_ids, approved, reason_codes, risk_policy_version` | 拒绝原因结构化、可审计；单个订单的决策可独立查询 |
| `Fill` | `fill_id, order_id, instrument_id, side, quantity, price, fee, filled_at` | 成交单价非负、数量正、费用非负、可追溯原订单 |
| `PortfolioState` | `as_of, cash, positions, marks, nav, ledger_version` | NAV = cash + Σ持仓市值（USD 单币示例），现金不可为负，无裸空头 |
| `BacktestReport` | `run_id, commit_sha, data_manifest_id, config_hash, nav_series, trades, metrics, assumptions` | 可追溯到输入及口径，不能缺失费用与成交假设 |

接口名称允许 Phase B 作兼容性评审后小范围调整，须新增 ADR 记录变更原因；进入稳定版本后按语义化版本处理破坏性改动。

## 3. 建议的 Protocol（伪接口）

```python
class DataProvider(Protocol):
    def snapshot(self, as_of: datetime) -> DataSnapshot: ...

class FactorBuilder(Protocol):
    def compute(self, snapshot: DataSnapshot) -> FactorFrame: ...

class Forecaster(Protocol):
    def predict(self, factors: FactorFrame, *, as_of: datetime) -> Forecast: ...

class Strategy(Protocol):
    def generate(self, forecast: Forecast) -> list[StrategySignal]: ...

class PortfolioAllocator(Protocol):
    def allocate(
        self, signals: list[StrategySignal], state: PortfolioState
    ) -> TargetPortfolio: ...

class RiskGate(Protocol):
    def review(
        self, target: TargetPortfolio, orders: list[OrderIntent],
        state: PortfolioState
    ) -> list[RiskDecision]: ...

class ExecutionSimulator(Protocol):
    def process_approved(
        self, orders: list[OrderIntent], decisions: list[RiskDecision],
        next_market_event: object
    ) -> tuple[list[Fill], PortfolioState]: ...

class Evaluator(Protocol):
    def evaluate(self, states: list[PortfolioState]) -> BacktestReport: ...
```

这些是**接口草案**，不是已可导入或已运行的 Python 代码。实际实现时要进一步指定显式 `ModelFitArtifact`、市场事件类型、订单转化器及配置类型。特别地，`Forecast` 的 `training_cutoff` 不应由测试时刻未来数据推得。

## 4. 模块职责与依赖方向

- `core` 不依赖领域模块。
- `finance` 可依赖 `core`，但不依赖 `execution` 或 `research`。
- `data` 依赖 `core`；`research` 依赖 `data + finance + core`。
- `models` 依赖 `core` 公共研究表示，不直接读交易执行状态。
- `strategies` 依赖 `core` 信号接口；`portfolio` 和 `risk` 依赖 `core + finance`。
- `execution` 和 `evaluation` 依赖 `core` 与必要的金融计算；运行编排层按照时间顺序组合全部模块，业务模块不彼此循环调用。

## 5. 明确的失败返回与拒绝原因

任何风险与执行拒绝不得静默发生，建议使用结构化原因：
`ASOF_VIOLATION`, `MISSING_BAR`, `STALE_MARK`, `INVALID_PRICE`,
`UNTRADEABLE`, `CASH_SHORTAGE`, `POSITION_LIMIT`, `NO_RISK_APPROVAL`,
`UNSUPPORTED_CORPORATE_ACTION`, `DUPLICATE_ORDER`。

缺失的预测目标不能转成值为零的预测；网络/文件失败不能返回空数据冒充市场无成交。

## 6. 第一条可验收链

在具有两天以上数据的样例中，T 日收盘后由 `DataSnapshot` 生成 `FactorFrame`，由 `Forecast` 转换成 `StrategySignal`，分配 `TargetPortfolio`，风控形成 `RiskDecision`。唯一获准的 `OrderIntent` 在 T+1 日开盘模拟 `Fill`，由账本计算 `PortfolioState`，由 `BacktestReport` 记录全流程。细化用例与数字基准见 `../validation/acceptance.md`。
