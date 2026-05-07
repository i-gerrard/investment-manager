# Investment Manager — 产品需求文档 (PRD)

**版本：** v1.0  
**日期：** 2026-05-07  
**仓库：** https://github.com/i-gerrard/investment-manager  
**技术栈：** Next.js + TypeScript + FastAPI + PostgreSQL + Docker

---

## 背景与目标

当前系统已有基础框架（Portfolio / Reports / Research / Stocks 页面），但两个核心使用场景尚未闭环：

1. **每日报告 → 组合快照**：`us-stock-report` skill 每天生成 HTML 报告（含 eToro + TR 双账户实时持仓），这些数据目前仅以静态 HTML 文件存在，无法在 Web UI 中历史查阅、趋势分析、或与交易记录联动。
2. **推荐操作 → 复盘验证**：报告中每天都有具体操作建议（如"挂单 $400 加仓 MSFT"），目前没有系统性工具跟踪这些建议是否执行、执行效果如何。

本文档定义以上两个模块的详细需求。

---

## 模块一：Daily Report Loader — 组合快照页

### 1.1 功能目标

将每日 HTML 报告的结构化数据导入数据库，在 Web 端呈现为可交互的 Portfolio 快照时间轴，支持横向对比多日持仓变化。

### 1.2 用户故事

| # | 角色 | 需求 | 验收标准 |
|---|------|------|---------|
| U1 | 投资者 | 上传当日 HTML 报告后，自动解析持仓数据 | 上传后 <3s 完成解析，展示持仓列表 |
| U2 | 投资者 | 查看任意历史日期的持仓快照 | 日历控件选日期，精确还原当日持仓 |
| U3 | 投资者 | 对比两个日期的持仓变化（股数/盈亏/仓位%） | 差异行高亮，新增/清仓标注 |
| U4 | 投资者 | 查看单只股票在所有快照中的价格/P&L 曲线 | 点击个股弹出时间序列折线图 |
| U5 | 投资者 | 查看合并总净值（eToro+TR）的历史走势 | 主页 Dashboard 集成总净值折线图 |
| U6 | 投资者 | 查看每日现金占比变化 | 现金/已投资比例折线图（颜色区间标注） |

### 1.3 数据解析规则

HTML 报告中需提取的字段：

**账户层面（每日一条 `portfolio_snapshot` 记录）**

```
report_date          DATE
etoro_total_usd      NUMERIC        -- eToro 总净值
etoro_cash_usd       NUMERIC        -- eToro 现金
etoro_invested_usd   NUMERIC        -- eToro 已投资
etoro_pnl_day_usd    NUMERIC        -- 今日 P&L
tr_total_eur         NUMERIC        -- TR 总净值
tr_cash_eur          NUMERIC        -- TR 现金
tr_invested_eur      NUMERIC        -- TR 已投资
tr_pnl_day_eur       NUMERIC        -- 今日 P&L
eur_usd_rate         NUMERIC        -- 汇率
combined_total_usd   NUMERIC        -- 合并总净值（计算字段）
combined_cash_usd    NUMERIC        -- 合并现金
cash_ratio_pct       NUMERIC        -- 现金占比 %
```

**持仓层面（每日每股一条 `holding_snapshot` 记录）**

```
snapshot_date        DATE
account              ENUM('etoro','tr')
ticker               VARCHAR(10)
shares               NUMERIC
avg_cost             NUMERIC
current_price        NUMERIC
market_value_usd     NUMERIC
pnl_total_usd        NUMERIC
pnl_total_pct        NUMERIC
pnl_day_usd          NUMERIC        -- 今日 P&L（如报告含此字段）
pnl_day_pct          NUMERIC        -- 今日涨跌幅
verdict              ENUM('buy','hold','sell')   -- 报告中的建议
```

### 1.4 解析器设计

报告 HTML 有固定 CSS 类名，解析规则稳定：

```
.account-box table tr  →  持仓行
td[0] = ticker, td[1] = price, td[2] = day_chg, td[3] = shares
td[4] = avg_cost, td[5] = pnl, td[6] = pnl_pct, td[7] = value
.combined-total .amount  →  合并总净值
.account-box .total  →  账户净值
.pnl-day  →  今日 P&L（从文本提取数字）
```

解析器以 Python 函数实现，放在 `backend/app/services/report_parser.py`。

### 1.5 前端页面结构

**路由：** `/portfolio/snapshots`

```
┌─────────────────────────────────────────────────────┐
│  Portfolio Snapshots          [上传报告 HTML]  [日历] │
├─────────────────────────────────────────────────────┤
│  总净值走势  ━━━━━━╮                               │
│  $253,863      ╰━━━━━╮  现金比例 6.4% 🟡           │
│                       ╰━━━  [选对比日期]            │
├──────────────┬──────────────────────────────────────┤
│  eToro       │  Trade Republic                      │
│  $91,706     │  €137,958                            │
│  现金 $5,904 │  现金 €XXX                           │
├──────────────┴──────────────────────────────────────┤
│  持仓表（可按账户/板块/P&L 排序）                    │
│  Ticker  股数  均价  现价  P&L  P&L%  今日  建议    │
│  NVDA    126  $163  $200  +22%  +$1.8k  +1.9%  BUY │
│  ...                                                │
│  [点击任意行 → 弹出单股历史曲线]                    │
└─────────────────────────────────────────────────────┘
```

**对比模式（选择两个日期）：**

```
  Ticker   05/06 持仓   05/07 持仓   变化      P&L 变化
  NVDA     126 股       126 股       —         +$371
  MSFT     64 股        64 股        —         -$104
  AMD      46.82 股     46.82 股     —         +$1,340  ← 财报日高亮
  META     30.08 股     30.08 股     —         -$72
```

### 1.6 API 端点（新增）

```
POST   /api/reports/upload          -- 上传 HTML，触发解析，返回 snapshot_id
GET    /api/snapshots               -- 列出所有快照日期
GET    /api/snapshots/{date}        -- 获取指定日期完整快照
GET    /api/snapshots/{date}/holdings  -- 持仓明细
GET    /api/snapshots/compare?from={d1}&to={d2}  -- 两日对比
GET    /api/holdings/{ticker}/history  -- 单股历史数据
GET    /api/portfolio/summary       -- 净值+现金走势（用于 Dashboard 图表）
```

### 1.7 数据库变更

新增两张表，挂在现有 `report.py` model 旁：

```sql
CREATE TABLE portfolio_snapshots (
    id              SERIAL PRIMARY KEY,
    report_date     DATE UNIQUE NOT NULL,
    etoro_total_usd NUMERIC(12,2),
    etoro_cash_usd  NUMERIC(12,2),
    tr_total_eur    NUMERIC(12,2),
    tr_cash_eur     NUMERIC(12,2),
    eur_usd_rate    NUMERIC(8,6),
    combined_total_usd NUMERIC(12,2),
    cash_ratio_pct  NUMERIC(5,2),
    raw_html        TEXT,          -- 原始 HTML 备份
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE holding_snapshots (
    id              SERIAL PRIMARY KEY,
    snapshot_id     INT REFERENCES portfolio_snapshots(id),
    account         VARCHAR(10),   -- 'etoro' | 'tr'
    ticker          VARCHAR(10),
    shares          NUMERIC(12,4),
    avg_cost        NUMERIC(10,4),
    current_price   NUMERIC(10,4),
    market_value_usd NUMERIC(12,2),
    pnl_total_usd   NUMERIC(12,2),
    pnl_total_pct   NUMERIC(8,4),
    pnl_day_pct     NUMERIC(8,4),
    verdict         VARCHAR(10),
    UNIQUE(snapshot_id, account, ticker)
);
```

---

## 模块二：Trade Review — 操作复盘模块

### 2.1 功能目标

将每日报告中的具体操作建议（如"挂单 $400 加仓 MSFT"）结构化存储，允许用户记录实际执行情况，并与模拟理论收益对比，形成可追溯的决策评估记录。

### 2.2 用户故事

| # | 角色 | 需求 | 验收标准 |
|---|------|------|---------|
| U1 | 投资者 | 查看某日报告中所有建议操作的列表 | 操作列表含：标的/方向/参考价/账户/理由 |
| U2 | 投资者 | 标记某条建议为"已执行"并填写实际成交价和股数 | 填写后显示实际 P&L |
| U3 | 投资者 | 标记某条建议为"未执行"并说明原因 | 支持下拉原因（忘了/不认同/无资金/等更好价格） |
| U4 | 投资者 | 对任意一条建议运行模拟复盘：输入假设买入价和卖出日期，系统计算理论盈亏 | 对比"模拟收益"vs"实际收益（或 0）" |
| U5 | 投资者 | 查看历史建议的整体命中率统计 | 按方向/标的/时间段聚合，命中率% + 平均理论收益 |
| U6 | 投资者 | 查看"未执行但理论上盈利"的遗憾清单 | 按遗憾程度（理论亏损/盈利金额）排序 |

### 2.3 核心概念定义

**操作建议（Recommendation）**：报告操作建议汇总表中每一行，属性包括：
- 来源报告日期
- 优先级（① 今日必须 / ② 关注 / ③ 等待 / ④ 持有）
- 标的 ticker
- 方向（加仓/止损上移/等待修复/等待低吸/持有）
- 账户（eToro / TR / 双账户）
- 参考价（挂单价或止损价）
- 理由（文本）

**执行记录（Execution）**：用户针对一条 Recommendation 记录的实际操作：
- 状态：已执行 / 未执行 / 部分执行
- 实际成交价
- 实际股数
- 执行日期
- 未执行原因（如适用）

**模拟复盘（Simulation）**：假设以某个价格买入/卖出，计算理论收益：
- 模拟买入价、模拟买入日期
- 模拟卖出价、模拟卖出日期（可选，默认取对应快照当日价格）
- 输出：理论盈亏（USD/EUR）、理论收益率、vs 实际收益差值

### 2.4 复盘工作流

```
[报告上传解析] → 自动提取建议列表（操作建议汇总表）
       ↓
[复盘页面] 展示建议列表，每行显示：
  - 建议详情
  - 执行状态（待填写 / 已执行 / 未执行）
  - 若已执行：实际 P&L（实时计算，用后续快照价格）
  - [运行模拟] 按钮

[点击"运行模拟"]
  → 弹窗：
      模拟买入价：___  股数：___  日期：___
      模拟卖出日期：___（或"当前持有"）
  → 显示结果：
      理论买入成本：$X,XXX
      当前/卖出价值：$X,XXX
      理论盈亏：+$XXX (+X.X%)
      vs 实际：若未执行则显示"遗憾成本：$XXX"
```

### 2.5 数据模型

```sql
CREATE TABLE recommendations (
    id              SERIAL PRIMARY KEY,
    snapshot_id     INT REFERENCES portfolio_snapshots(id),
    report_date     DATE NOT NULL,
    priority        VARCHAR(20),   -- '① 今日必须' | '② 关注' | '③ 等待' | '④ 持有'
    ticker          VARCHAR(10),
    direction       VARCHAR(30),   -- 'buy' | 'sell' | 'hold' | 'stop_loss_move' | 'wait'
    account         VARCHAR(10),
    reference_price NUMERIC(10,4),
    rationale       TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE executions (
    id                  SERIAL PRIMARY KEY,
    recommendation_id   INT REFERENCES recommendations(id),
    status              VARCHAR(20),   -- 'executed' | 'skipped' | 'partial'
    actual_price        NUMERIC(10,4),
    actual_shares       NUMERIC(12,4),
    execution_date      DATE,
    skip_reason         VARCHAR(50),   -- 'forgot' | 'disagreed' | 'no_cash' | 'waiting_better_price' | 'other'
    skip_note           TEXT,
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE simulations (
    id                  SERIAL PRIMARY KEY,
    recommendation_id   INT REFERENCES recommendations(id),
    sim_entry_price     NUMERIC(10,4),
    sim_entry_date      DATE,
    sim_entry_shares    NUMERIC(12,4),
    sim_exit_price      NUMERIC(10,4),
    sim_exit_date       DATE,          -- NULL = 当前持有
    sim_pnl_usd         NUMERIC(12,2), -- 计算字段
    sim_pnl_pct         NUMERIC(8,4),  -- 计算字段
    actual_pnl_usd      NUMERIC(12,2), -- 对应 execution 的实际 P&L
    regret_usd          NUMERIC(12,2), -- sim_pnl - actual_pnl（遗憾成本）
    created_at          TIMESTAMP DEFAULT NOW()
);
```

### 2.6 前端页面结构

**路由：** `/review`

```
┌─────────────────────────────────────────────────────────┐
│  操作复盘                    [日期筛选]  [标的筛选]  [状态]│
├────────────────────────────────────────────────────────┤
│  总览统计（当前筛选范围内）                               │
│  建议总数: 42  已执行: 18 (43%)  未执行: 24 (57%)        │
│  执行建议均收益: +8.3%    未执行建议理论均收益: +11.2%    │
│  最大遗憾: AMD +15% (5/6, 未执行)                        │
├─────────────────────────────────────────────────────────┤
│  建议列表                                                │
│  日期    标的  方向     参考价  优先级  状态    P&L  操作  │
│  05/06  MSFT  加仓     $400   ②关注   ⏳待填  —    [填写] │
│  05/06  AMD   止损上移  $330   ②关注   ✅执行  +$X  [详情] │
│  05/06  META  等待修复  $642   ③等待   ❌跳过  —    [模拟] │
│  05/06  NVDA  等待低吸  $190   ③等待   ⏳待填  —    [填写] │
└─────────────────────────────────────────────────────────┘

[点击"模拟"弹窗]
┌────────────────────────────────────┐
│  模拟复盘 — META  (建议日: 05/06)   │
│  建议：等待修复，均价 $642          │
│  ─────────────────────────────    │
│  模拟买入价  $___  股数  ___       │
│  买入日期    ____                  │
│  模拟卖出    ○ 今日价  ○ 指定日期  │
│  ─────────────────────────────    │
│  理论成本    $0                    │
│  理论价值    $0                    │
│  理论盈亏    —                     │
│  遗憾成本    —（未执行时显示）      │
│              [运行]  [关闭]        │
└────────────────────────────────────┘
```

**遗憾清单 Tab（`/review/regrets`）**

```
  标的   建议日   方向    未执行原因   理论收益   遗憾成本
  AMD   05/06  加仓$350  无资金      +$2,104    +$2,104
  NVDA  04/28  $185低吸  不认同      +$840      +$840
  ...
```

### 2.7 API 端点（新增）

```
GET    /api/recommendations                     -- 建议列表（支持筛选）
GET    /api/recommendations/{id}                -- 单条建议详情
POST   /api/recommendations/{id}/execute        -- 记录执行情况
POST   /api/recommendations/{id}/skip           -- 记录跳过原因
POST   /api/simulations                         -- 运行模拟（返回计算结果）
GET    /api/review/stats                        -- 命中率统计
GET    /api/review/regrets                      -- 遗憾清单（按遗憾金额排序）
```

---

## 实施优先级与分阶段计划

### Phase 1 — 数据基础（约 2 周）

| 任务 | 文件 | 说明 |
|------|------|------|
| 新增数据库表 | `backend/app/models/` | portfolio_snapshots, holding_snapshots |
| HTML 解析器 | `backend/app/services/report_parser.py` | 解析现有 HTML 报告格式 |
| 上传 API | `backend/app/api/reports.py` | POST /api/reports/upload |
| 快照查询 API | `backend/app/api/snapshots.py` | GET 系列端点 |

### Phase 2 — 组合快照页（约 1.5 周）

| 任务 | 文件 | 说明 |
|------|------|------|
| 快照列表页 | `frontend/src/app/portfolio/snapshots/` | 日历 + 持仓表 |
| 总净值走势图 | `frontend/src/components/charts/` | recharts 折线图 |
| 对比模式 | `frontend/src/app/portfolio/compare/` | 双日期选择 + diff 表 |
| Dashboard 集成 | `frontend/src/app/dashboard/` | 总净值 + 现金比例迷你图 |

### Phase 3 — 复盘模块（约 2 周）

| 任务 | 文件 | 说明 |
|------|------|------|
| Recommendation 解析 | `backend/app/services/report_parser.py` | 扩展：提取操作建议表 |
| 新增数据库表 | `backend/app/models/` | recommendations, executions, simulations |
| 复盘 CRUD API | `backend/app/api/review.py` | execute / skip / simulate |
| 复盘列表页 | `frontend/src/app/review/` | 建议列表 + 状态标注 |
| 模拟弹窗组件 | `frontend/src/components/SimulationModal.tsx` | 输入+计算+展示 |
| 遗憾清单页 | `frontend/src/app/review/regrets/` | 排序 + 筛选 |
| 统计 Dashboard | `frontend/src/app/review/stats/` | 命中率 + 均收益 |

### Phase 4 — 自动化集成（可选，约 1 周）

- CLI 命令 `claude upload-report {file}` → 直接调用上传 API + 解析
- 与 `us-stock-report` skill 联动：报告生成后自动 POST 到本地服务

---

## 非功能性需求

| 维度 | 要求 |
|------|------|
| 性能 | 快照页加载 < 1s（持仓 ≤ 30 条），历史查询 < 500ms |
| 安全 | 沿用现有 JWT Auth，所有 `/api/` 端点需鉴权 |
| 数据完整性 | HTML 解析失败时回滚事务，不写入半条记录 |
| 向后兼容 | HTML 报告格式变化时，解析器抛出明确错误而非静默跳过 |
| 移动端 | 复盘模块需在 375px 宽度下可用（模拟弹窗全屏覆盖） |

---

## 开放问题（实施前需确认）

1. **建议自动提取精度**：报告中操作建议汇总表的结构是否固定？（当前版本是固定 CSS 类名的 `<table>`，预计可稳定解析）
2. **历史报告导入**：是否需要一次性批量导入过去所有 HTML 报告？
3. **TR 现金余额**：TR 页面现金字段在 JS 提取失败时是否允许手动输入作为 fallback？
4. **模拟价格来源**：运行历史模拟时，卖出价从哪里取——数据库快照表（仅每日一次），还是接入实时行情 API？
5. **多币种统一**：TR 持仓以 EUR 计价，模拟盈亏是否统一转换为 USD 显示？

---

*文档由 Claude Sonnet 4.6 生成 | 2026-05-07*
