# 增强模块参考文档 (Enhancement Modules Reference)

> 创建日期: 2026-06-29
> 目的: 补齐管线在「横向/纵向对比 + 全球宏观 + 科技主线 + 资金流确认」维度的结构性缺口

---

## 概述

四个新增/增强模块，解决以下问题：

| 问题 | 解决模块 | 集成位置 |
|------|---------|---------|
| 无日韩/亚太市场板块动量数据 | `fetch_asia_market_momentum.py` | Stage 1, 9 |
| 增长分析偏回顾性，缺少拐点前瞻 | `detect_growth_inflection.py` | Stage 5, 6 |
| Roadmap-Walker 缺少地理维度 | `score_bottleneck_asymmetry.py` + `roadmap-walker.md` 增强 | Stage 8, walk mode |
| 筛选缺少资金流过滤，报告缺少估值/资金指标 | `compute_money_flow.py` | Stage 4, 11, 16 |

---

## 模块 1: `fetch_asia_market_momentum.py`

### 定位
亚洲市场（日本/韩国/中国/台湾）板块动量与相对强弱追踪。回答「全球科技资金往哪流？亚洲哪个市场最强？」

### 调用方式
```bash
# 全部区域
uv run python scripts/fetch_asia_market_momentum.py

# 只看日韩
uv run python scripts/fetch_asia_market_momentum.py --groups japan,korea

# 指定benchmark和输出文件
uv run python scripts/fetch_asia_market_momentum.py --benchmark QQQ --output reports/asia.json

# 快速看指数趋势
uv run python scripts/fetch_asia_market_momentum.py --groups indices
```

### ETF 覆盖范围

| 区域 | 宽基ETF | 板块/个股 |
|------|---------|-----------|
| 🇯🇵 日本 | EWJ, JPXN, BBJP, DXJS, FLJP | BOTZ(机器人), 半导体代理 |
| 🇰🇷 韩国 | EWY, FLKR, KORU | 005930.KS(三星), 000660.KS(SK海力士), 373220.KS(LG新能源), 006400.KS(三星SDI), 035420.KS(Naver), 035720.KS(Kakao) |
| 🇨🇳 中国/HK | KWEB, MCHI, FXI, CXSE, 2800.HK | 覆盖互联网、大盘、非国企 |
| 🇹🇼 台湾 | EWT | TSM (台积电ADR) |
| 📊 指数对比 | ^N225, ^KS11, ^HSI, ^TWII, 000001.SS | 与SPY/QQQ对标 |

### 计算逻辑

```
每个标的:
├─ 收益率: 1D, 5D, 1M, 3M, 6M
├─ RS比率: ETF价格 / SPY价格 (归一化)
├─ RS变化: 各时段RS变化百分比
├─ RS动量: 1M vs 3M RS变化 → 方向标签
├─ 成交量比: 5D均量 / 20D均量
└─ 综合RS评分: 加权 (1M:15%, 3M:30%, 6M:30%, 12M:25%) + 动量奖惩

区域汇总:
├─ composite_rs: 区域整体RS评分
├─ direction: 区域趋势方向
└─ top_sector: 区域最强板块
```

### 跨市场分析输出 (cross_market_analysis)

| 指标 | 含义 | 用途 |
|------|------|------|
| `tech_leadership` | 哪个亚洲区域科技最强(3M RS最高) | 科技主线的地理判断 |
| `semiconductor_momentum` | 韩台日半导体综合动量评分(1-10) | 半导体周期定位 |
| `risk_appetite` | 亚洲风险资产(EWJ+EWY+KWEB) vs SPY | 全球资金流向信号 |
| `asia_vs_us_tech` | 亚洲科技平均RS vs QQQ | 中美科技相对强弱 |
| `signals` | 自动生成的观察信号数组 | 宏观判断辅助 |

### 自动集成点

- **Stage 1 (数据采集)**: `data-collector` 调用，与 `fetch_market_breadth.py`、`fetch_theme_performance.py` 并行
- **Stage 9 (宏观分析)**: `macro-analyst` 读取输出，结合全球宏观判断亚洲市场定位
- **Screening**: 为行业筛选提供「亚洲科技相对强弱」背景

---

## 模块 2: `detect_growth_inflection.py`

### 定位
前瞻性增长拐点检测。回答「这家公司的增长是在加速还是减速？有没有新业务正在爆发？」

### 调用方式
```bash
# 基础用法（从 fetch_financials.py 输出读取）
uv run python scripts/detect_growth_inflection.py reports/raw-data.json

# 带段数据
uv run python scripts/detect_growth_inflection.py reports/raw-data.json \
  --segments-json reports/segments.json

# 带同行对比
uv run python scripts/detect_growth_inflection.py reports/raw-data.json \
  --peer-growth-json reports/peer_growth.json \
  --output reports/inflection.json
```

### 五维度检测模型

#### 1️⃣ 收入加速度 (Revenue Acceleration) — 权重30%
```
评分范围: -5 ~ +5
检测方法:
├─ 计算每季度YoY增长率
├─ 计算加速度 = growth[t] - growth[t-1] (一阶导)
├─ 计算加加速度 = accel[t] - accel[t-1] (二阶导)
└─ 拐点信号:
   • 加速度符号翻转 (负→正 = 增长见底)
   • 连续2+季度正加速度 = 确认加速
   • 幅度: >5pp = 强信号

实际意义: 「不看增长本身，看增长的变化速度」
  +5 = 强加速 (如从+10%→+15%→+22%)
  -5 = 强减速 (如从+30%→+20%→+12%)
```

#### 2️⃣ 业务结构变迁 (Segment Mix Shift) — 权重20%
```
评分范围: 0 ~ 10
检测方法:
├─ 追踪各业务段占总收入比例
├─ 最快增长段 vs 公司平均增速
└─ 拐点信号:
   • 某段从 <10% 涨到 >20% (4-6季度内)
   • 最快段增速 > 2× 公司均值
   • 段数变化 (多元化 or 聚焦)

实际意义: 「新业务从边缘走向核心」
  10 = 明显的第二增长曲线出现
   0 = 结构稳定无变化
```

#### 3️⃣ 利润率体制变化 (Margin Regime Change) — 权重25%
```
评分范围: -5 ~ +5
检测方法:
├─ 追踪毛利率 + 经营利润率 (季度)
├─ 8季度线性回归拟合趋势斜率
└─ 拐点信号:
   • 斜率符号翻转 (压缩→扩张)
   • 跨越关键门槛 (如>40%毛利率 = 软件级经济性)
   • 经营杠杆启动: 收入增速 > 费用增速连续3Q+

实际意义: 「规模效应开始显现 or 竞争加剧」
  +5 = 结构性扩张 (规模效应/产品成熟/定价权)
  -5 = 结构性压缩 (竞争加剧/成本上涨/产品老化)
```

#### 4️⃣ 研发转化启动 (R&D-to-Revenue Transmission) — 权重15%
```
评分范围: 0 ~ 10
检测方法:
├─ 追踪 R&D% = R&D支出 / 收入
├─ 对比 R&D增速 vs 收入增速
└─ 拐点信号:
   • R&D% 下降 + 收入加速 (投入开始回报)
   • 收入增速 > R&D增速 连续3Q+
   • 同时毛利率扩张 (产品成熟信号)

实际意义: 「前期研发投入开始变现」
  10 = 清晰的R&D回报期 (如新药上市/新产品放量)
   0 = 仍在投入期，回报未见
```

#### 5️⃣ 客户/收入集中度变化 (Concentration Change) — 权重10%
```
评分范围: -5 ~ +5
检测方法:
├─ 从地理/业务段数据推算HHI
├─ 追踪HHI变化趋势
└─ 拐点信号:
   • HHI显著下降 = 健康多元化 (规模化信号)
   • HHI骤升 = 新大客户 (增长但有集中风险)
   • 国际收入占比突变 = 全球化拐点

实际意义: 「从依赖单一市场→多点开花」
  +5 = 健康多元化扩张
  -5 = 危险的客户/地域集中
```

### 综合评分与判定

```
复合分 = Σ(维度分 × 权重) / Σ(可用维度权重)  归一化到 [-10, +10]

判定标准:
┌────────────────┬────────────────────────────────────────┐
│ +7 ~ +10       │ STRONG_POSITIVE_INFLECTION (业务转型中) │
│ +3 ~ +6        │ MODERATE_POSITIVE_INFLECTION (增长再加速)│
│ -2 ~ +2        │ NO_INFLECTION (稳定轨迹)                │
│ -6 ~ -3        │ MODERATE_NEGATIVE_INFLECTION (增长见顶)  │
│ -10 ~ -7       │ STRONG_NEGATIVE_INFLECTION (结构性下滑)  │
└────────────────┴────────────────────────────────────────┘
```

### 附加输出

| 字段 | 含义 |
|------|------|
| `inflection_type` | acceleration / deceleration / model_shift / margin_expansion / none |
| `confidence` | 0-1, 数据完整度越高越可信 |
| `time_to_inflection_quarters` | 预计拐点完全显现的季度数 |
| `peer_relative` | AHEAD / INLINE / BEHIND (相对同行) |
| `key_evidence` | 3-5条支撑拐点判断的关键证据 |
| `risk_to_thesis` | 什么情况会证伪这个拐点信号 |

### 自动集成点

- **Stage 5 (基本面)**: `fundamental-analyst` 在分析产品管线和历史业绩后调用
- **Stage 6 (盈利质量)**: 补充盈利加速/减速的前瞻判断
- **Stage 16 (评分)**: 拐点评分作为 conviction 调节因子

---

## 模块 3: `score_bottleneck_asymmetry.py` 地理维度增强 + `roadmap-walker.md` 更新

### 定位
在价值链拆解时标注每层的**地理主导国**和**地缘风险**。回答「这个瓶颈在哪个国家？如果中美脱钩会怎样？」

### 新增CLI参数

```bash
uv run python scripts/score_bottleneck_asymmetry.py \
  --tech-uniqueness 1 \
  --capex-years 3.5 \
  --top5-buyer-pct 72 \
  --vertical-resist 1 \
  --asymmetry-ratio 0.08 \
  --inst-own-pct 25 \
  # ↓ 新增地理参数 ↓
  --geo-leader TW \
  --geo-hhi 6500 \
  --geo-risk-flags '["taiwan_strait", "us_export_control"]' \
  --geo-policy-support strong_national_priority \
  --geo-alternatives 1
```

### 新增第7维度: `geo_strategic_score`

```
权重分配 (有地理数据时):
┌──────────────────┬────────┬──────────┐
│ 维度              │ 旧权重  │ 新权重   │
├──────────────────┼────────┼──────────┤
│ chokepoint       │ 30%    │ 27%     │
│ capex_lead       │ 15%    │ 14%     │
│ buyer_conc       │ 15%    │ 14%     │
│ vertical_resist  │ 10%    │ 9%      │
│ asymmetry_ratio  │ 20%    │ 18%     │
│ earliness        │ 10%    │ 8%      │
│ geo_strategic    │ -      │ 10% ← NEW │
└──────────────────┴────────┴──────────┘
(无地理数据时自动退回原6维度权重，完全向后兼容)
```

### 地理评分计算

```
geo_strategic_score (0-100) 由4个子项构成:

1. concentration_risk (30%权重):
   HHI > 5000 → 高集中 (分数0-30, 集中=高风险=低分... 
   实际逻辑: 高集中 = 更强瓶颈 = 高分)
   HHI 2500-5000 → 中等 (30-60)
   HHI < 2500 → 分散 (60-100)
   
2. policy_tailwind (30%权重):
   strong_national_priority = 100 (如CHIPS Act, K-半导体)
   moderate_subsidy = 60
   weak = 30
   none = 0

3. alternative_scarcity (30%权重):
   0个替代国 = 100 (绝对稀缺)
   1个 = 75
   2个 = 50  
   3个+ = 25

4. risk_penalty (减分项):
   每个风险标签 = -10分 (最低0)
   
最终: geo_strategic = (conc×0.3 + policy×0.3 + alt×0.3) - risk_penalty
```

### 风险标签清单

| 标签 | 含义 |
|------|------|
| `us_export_control` | 美国出口管制影响 |
| `china_tariff` | 中国关税/贸易摩擦 |
| `taiwan_strait` | 台海地缘风险 |
| `korea_north_risk` | 朝鲜半岛风险 |
| `japan_yen_weakness` | 日元贬值影响 |
| `china_tech_crackdown` | 中国科技监管风险 |
| `eu_regulation` | 欧盟监管 (如芯片法案合规) |
| `sanctions_risk` | 制裁风险 |

### Roadmap-Walker Agent 更新

#### Step 2 (链路拆解) 新增字段
每层现在必须标注:
- `geo_leader`: 主导国家/地区
- `geo_leader_share_pct`: 主导者的全球市占率
- `geo_hhi`: 地理集中度HHI
- `geo_risk_flags`: 地缘风险标签
- `geo_policy_support`: 政策支持级别
- `geo_alternatives`: 替代国供应商数量

#### Step 6 (综合输出) 新增部分

**Section 6: Geographic Risk Map**
```markdown
| Layer | Geo Leader | Share% | HHI | Risk Flags | Alternatives |
|-------|-----------|--------|-----|------------|--------------|
| Foundry | TW | 65% | 6500 | taiwan_strait | 1 (KR) |
| Equipment | NL/JP | 80% | 5200 | us_export_control | 0 |
| Materials | JP | 55% | 4800 | japan_yen_weakness | 2 (KR, DE) |
```

**Section 7: Policy Tailwind Summary**
哪些候选标的享受国家政策支持 (CHIPS Act, K-Semiconductor, 大基金等)

**Section 8: Geopolitical Scenario Brief**
如果中美关系进一步恶化，链路中哪些环节最脆弱？替代方案？

#### 科技主线地理参考表 (新增)
```
┌──────┬──────────────────────────────────────────────┐
│ 🇺🇸 US │ 设计(Fabless)、EDA、云平台、AI框架、GPU架构      │
│ 🇯🇵 JP │ 材料(光刻胶/硅片)、设备(TEL)、机器人、传感器     │
│ 🇰🇷 KR │ 存储(DRAM/NAND)、电池、显示面板、造船           │
│ 🇹🇼 TW │ 代工(Foundry)、先进封装(CoWoS)、IC设计服务     │
│ 🇨🇳 CN │ 组装、稀土、光伏/EV、消费互联网、成熟制程         │
│ 🇪🇺 EU │ 设备(ASML)、汽车芯片(Infineon)、工业自动化      │
└──────┴──────────────────────────────────────────────┘
```

### 自动集成点

- **Walk mode**: `roadmap-walker` 拆解链路时自动收集地理信息并传入scorer
- **Stage 8 (供应链)**: `supply-chain-analyst` 可调用地理增强版评分
- **报告输出**: walk.md 自动包含地理风险地图和地缘情景分析

---

## 管线流转图 (三模块如何嵌入)

```
                          ┌─────────────────────────────┐
                          │    Pipeline Execution Flow    │
                          └─────────────────────────────┘
                                       │
  Stage 1 (数据采集) ─────────────────────┤
  │                                     │
  ├─ fetch_market_breadth.py            │
  ├─ fetch_theme_performance.py         │
  ├─ fetch_asia_market_momentum.py ← NEW│ ← 日韩中台市场动量
  ├─ compute_sector_rs.py              │
  └─ fetch_macro.py                    │
                                       │
  Stage 5-6 (基本面) ─────────────────────┤
  │                                     │
  ├─ fetch_financials.py               │
  ├─ calculate_metrics.py              │
  ├─ calculate_earnings_quality.py     │
  └─ detect_growth_inflection.py ← NEW │ ← 增长拐点检测
                                       │
  Stage 8 / Walk Mode ────────────────────┤
  │                                     │
  ├─ roadmap-walker (增强版) ← ENHANCED │ ← 地理维度采集
  └─ score_bottleneck_asymmetry.py     │
     (7维度版) ← ENHANCED              │ ← 地理战略评分
                                       │
  Stage 9 (宏观) ─────────────────────────┤
  │                                     │
  ├─ fetch_global_macro.py             │
  └─ [读取 asia_momentum 输出] ← NEW   │ ← 亚洲市场定位
                                       │
  Stage 16-17 (评分/报告) ────────────────┤
  │                                     │
  ├─ compute_scores.py                 │
  │  └─ 拐点分作为conviction调节        │
  └─ equity-report-writer              │
     └─ 地理风险/亚洲趋势写入报告正文    │
```

---

## 实际应用场景示例

### 场景1: 筛选科技主线受益标的
```
用户: "找AI算力链上最有潜力的标的"

执行流程:
1. fetch_asia_market_momentum → 发现韩国半导体板块 3M RS = +12% (最强)
2. roadmap-walker --mode walk "AI datacenter infrastructure"
   → 链路拆解，每层标注geo_leader
   → HBM层: KR主导 (SK Hynix), geo_hhi=7000, policy=K-Semiconductor
   → CoWoS层: TW主导 (TSMC), geo_hhi=8500, risk=taiwan_strait
3. score_bottleneck_asymmetry → 带地理维度的综合评分
4. detect_growth_inflection → SK Hynix: revenue_acceleration=+4.5 (HBM放量)
5. compute_money_flow → SK Hynix: 连续5日净流入, 量价齐升✓, score=8.2

输出: "SK Hynix 在HBM环节享受瓶颈溢价+国策支持+增长拐点+资金确认 四重叠加"
```

### 场景2: 验证个股增长逻辑
```
用户: "分析台积电的增长前景"

执行流程:
1. fetch_financials → 季度数据
2. detect_growth_inflection → 
   revenue_acceleration: +3.8 (AI芯片驱动)
   segment_shift: 7.2 (先进制程占比从45%→62%)
   margin_regime: +2.5 (3nm良率提升带来经营杠杆)
   verdict: MODERATE_POSITIVE_INFLECTION
3. asia_market_momentum → 台湾 EWT RS +8% vs SPY
4. 地理风险: taiwan_strait flag, geo_hhi=8500
5. compute_money_flow → TSM: 连续3日流入, 量比1.4, 量价对称✓

输出: "增长拐点确认(先进制程放量)+资金面配合，但地理集中风险极高"
```

### 场景3: 筛选时过滤资金流出的股票
```
用户: "筛选出来的股票都是净流出的"

解决方案 (现已内置):
1. company-screener Stage 4 自动调用 compute_money_flow.py
2. 输出表格强制包含: 资金流向 | 连续流入天数 | 量价对称
3. STRONG_OUTFLOW 标记 CAUTION 标签
4. VOLUME_PRICE_SYMMETRY 给予 +1 加分
5. 最终排名中，量价齐升的标的天然获得更高评分

示例输出表格:
| 排名 | 标的 | 股价 | P/B | TTM PE | Fwd PE | 资金流向 | 连续流入 | 量价对称 |
|------|------|------|-----|--------|--------|----------|----------|----------|
| 1 | ANET | $82 | 12.5 | 35.2 | 28.4 | 强流入 | 5天 | ✓ |
| 2 | MRVL | $68 | 5.8 | 42.1 | 32.6 | 温和流入 | 3天 | ✓ |
| 3 | CDNS | $95 | 18.2 | 48.5 | 40.1 | 中性 | 0天 | ✗ |
| ⚠️4 | PLTR | $45 | 22.1 | 95.3 | 65.2 | 强流出 | -4天 | ✗ |
```

---

## 模块 4: `compute_money_flow.py`

### 定位
资金流确认引擎。核心逻辑：**连续多天净流入 + 成交量递增 = 量价齐升确认**。回答「机构在买吗？资金面支撑吗？」

### 调用方式
```bash
# 单个标的
uv run python scripts/compute_money_flow.py AAPL

# 多个标的
uv run python scripts/compute_money_flow.py AAPL NVDA TSM 000660.KS

# 自定义参数
uv run python scripts/compute_money_flow.py AAPL \
  --lookback 90 \
  --min-streak 5 \
  --output reports/money_flow.json
```

### 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `TICKER` | (必填) | 1个或多个股票代码 |
| `--lookback` | 60 | 分析回看天数 |
| `--min-streak` | 3 | 多少天连续流入才算显著信号 |
| `--output` | stdout | 输出文件路径 |

### 核心计算逻辑

```
每日流向判定 (3票表决):
├─ MFI-14 > 50 → 流入票 (+1)
├─ OBV 今日 > 昨日 → 流入票 (+1)
├─ CMF-20 > 0 → 流入票 (+1)
└─ 得票 ≥ 2/3 = "inflow day"

连续性检测:
├─ 计算当前连续流入天数 (current_streak)
├─ 计算回看期内最长流入连续 (max_inflow_streak)
└─ 记录每段连续流入/流出的起止日期和均量比

量价对称判定 (量价齐升):
├─ 条件1: 连续流入 ≥ min_streak 天 ✓
├─ 条件2: 期间均量 > 20日均量 (volume_ratio > 1.0) ✓
├─ 条件3: 成交量日内递增趋势 (volume_trend_rising) ✓
└─ 三者同时满足 = 真正的「量价齐升」
```

### 5维度综合评分 (0-10)

```
┌────────────────────────┬───────┬──────────────────────────────────┐
│ 维度                    │ 权重  │ 评分逻辑                          │
├────────────────────────┼───────┼──────────────────────────────────┤
│ 1. 连续流入强度         │ 30%  │ 5天+=10, 4天=8, 3天=6, 流出=-0   │
│ 2. 成交量确认           │ 25%  │ 量比>2=10, 1.5-2=8, 1-1.5=4-6   │
│ 3. 量价对称度           │ 25%  │ 流入+量增=10, 流入+量平=6,        │
│    (最重要的信号)       │      │ 流入+量减=3(背离!), 流出+量减=4   │
│ 4. MFI水平              │ 10%  │ 55-70(甜区)=10, >70=8, <30=1    │
│ 5. OBV趋势             │ 10%  │ 5D+20D都上升=10, 都下降=0        │
└────────────────────────┴───────┴──────────────────────────────────┘
```

### 判定标准

```
┌──────────────┬────────────────────────────────────────────────┐
│ 8-10 分       │ STRONG_INFLOW (量价齐升, 机构持续买入)            │
│ 6-7.9 分      │ MODERATE_INFLOW (有资金关注但未确认趋势)          │
│ 4-5.9 分      │ NEUTRAL (资金面中性)                             │
│ 2-3.9 分      │ MODERATE_OUTFLOW (资金流出, 谨慎)                │
│ 0-2 分        │ STRONG_OUTFLOW (持续放量流出, 回避)               │
└──────────────┴────────────────────────────────────────────────┘
```

### 信号标签

| 标签 | 含义 | 触发条件 |
|------|------|----------|
| `CONSECUTIVE_INFLOW_N_DAYS` | 连续N日净流入 | streak ≥ min_streak |
| `VOLUME_EXPANDING` | 成交量放大 | 5D/20D 量比 > 1.2 |
| `VOLUME_PRICE_SYMMETRY` | **量价齐升确认** | 连续流入 + 量递增 |
| `DIVERGENCE_WARNING` | 量价背离警告 | 价涨但OBV跌/价跌但OBV涨 |
| `SELLING_EXHAUSTION` | 抛压衰竭 | 流出中但量递减 |
| `OVERBOUGHT_FLOW` | 短期过热 | MFI > 80 |
| `OVERSOLD_FLOW` | 超卖可能反弹 | MFI < 20 |

### 估值快照 (每次必输出)

每个标的自动附带:
- `pb_ratio`: 市净率 (P/B)
- `pe_trailing`: 静态市盈率 (TTM P/E)
- `pe_forward`: 动态市盈率 (Forward P/E)
- `peg_ratio`: PEG比率
- `market_cap`: 总市值

### 自动集成点

```
Stage 4 (筛选):
├─ company-screener 对所有候选标的调用
├─ STRONG_OUTFLOW 标记 CAUTION (不自动剔除，但标记)
├─ VOLUME_PRICE_SYMMETRY 给予 +1 评分加分
└─ 输出表格强制显示资金流6列

Stage 11 (量化分析):
├─ quant-analyst 对分析标的调用
├─ 输出写入 stage11.md "Money Flow Confirmation" 章节
└─ 连续流入≥3天 + 量价对称 = "CONFIRMED institutional accumulation"

Stage 16 (评分):
├─ compute_scores.py 新增 money_flow_confirmation 维度
├─ 中期报告权重: 5% (从 macro_tailwind 中分出)
├─ 短期报告权重: 5% (从 alternative_alignment 中分出)
└─ 长期报告: 不纳入 (资金流是中短期信号)

Stage 17 (报告):
├─ 所有公司表格强制包含:
│   当前股价 | 市净率(P/B) | 静态PE | 动态PE | 资金流向 | 连续流入天数
└─ equity-report-writer guardrail 强制执行
```

---

## 维护说明

- 所有脚本遵循管线统一模式: yfinance数据源、argparse CLI、JSON stdout输出
- 向后兼容: 不提供新参数时行为与旧版一致
- ETF列表可能需要定期更新 (如新的韩国科技ETF上市)
- 韩国个股 (.KS) 数据偶有中断，脚本已内置 graceful degradation
- MFI/OBV/CMF 手动实现，不依赖 pandas-ta (更稳定)
