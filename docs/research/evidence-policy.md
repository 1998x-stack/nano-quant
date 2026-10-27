# 原始数据、研究证据与复现实验规范（Phase A）

## 1. 原始材料优先级

为每个量化研究假设建立最小证据链：
1. 市场：交易所历史行情/交易状态/公司行为/交易规则，或具授权且可追溯的供应商数据。
2. 财务：公司原始公告、监管申报及可核对公布日期的结构化财务记录。
3. 宏观：中央银行、统计机构的发布日历、首发值与 historical vintage（如适用）。
4. 理论：研究提出者的原始论文、公式、样本定义及方法限制。
5. 技术：Git、Python、依赖库、交易场所的官方规范/文档。

二手资料只作发现线索，不能替代原始事实验证。若第一手数据需要付费或许可，先记录可用性、限制及费用，不规避授权；v1.0 可先用明确标注的合成数据完成工程验收。

来源例子（访问前由实施者核验最新接口与条款）：SEC EDGAR、交易所官方历史市场数据、FRED/ALFRED、上市公司原始披露、Git 官方文档、Python 官方文档。**来源列表不意味着这些数据已经接入。**

## 2. 数据集 Manifest 必填

```yaml
dataset_id: synthetic-equities-v1
source_name: generated-fixture
source_url: null
license_or_permission: internal-synthetic
market: simulated-equities
time_coverage: "specified-in-fixture"
retrieved_at: "UTC timestamp at generation"
source_version: "fixture generator version"
file_hashes: {}
schema_version: "1"
timestamp_policy: "available_at / event_at / ingested_at"
adjustment_policy: "raw-price; corporate-actions: none"
universe_policy: "fixed synthetic set, no real-world survivorship claim"
limitations:
  - "No evidence about real market predictability"
```

真实资料还需包括原始文件 hash、供应商标识、修订信息、交易日历、资产标识映射、币种和时区。输入不可复现时，应降级结论。

## 3. 研究计划卡（在跑大规模实验前记录）

- `research_id`、提出日期、作者/负责人
- 金融或经济机制与可证伪假设
- universe 与排除规则
- 因子及目标收益定义、重平衡频率、可得时间
- 无风险利率/价格调整/退市/现金分红约定
- 训练、验证、最终留出区间；标签 horizon 与 purge/embargo（如需要）
- 对比基线：现金、等权、简单动量或与假设相关的朴素模型
- 统计检验、效应量与不确定性报告；多重比较控制计划
- 滑点/费用/持仓约束与容量假设
- 明确的否决条件及研究局限

## 4. 禁止的结论跳跃

- 单个历史区间回测盈利 => 不可推断稳健 Alpha。
- 没有公司行为、退市和许可核验的数据 => 不可宣称真实可交易历史收益。
- 因子显著相关 => 不自动证明因果关系。
- 预测准确率高 => 不自动证明扣费后可盈利。
- 单元测试全绿 => 不自动证明实盘风险可接受。

真实策略宣称研究成功前须有未参与开发的数据、稳定性/敏感性检验、可重复性与独立基准。

## 5. 实验 Artifact 最小集合

```text
run-manifest.json
config.yaml
environment-lock.txt
data-manifest.yaml
code-revision.txt
metrics.json
trade-ledger.csv
equity-curve.csv
research-notes.md
```

这些是 Phase B/C 需要实现的输出契约；当前目录中的文件并不代表已执行实验。
