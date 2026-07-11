# 多市场医药股票数据采集与分析 — 工作计划

> 基于 `stock_data_spec.yaml` 规范文件  
> 创建日期: 2026-07-11

---

## 一、标的概览

| # | 公司 | 上市模式 | 市场 | 代码 | 货币 | 上市日期 |
|---|------|---------|------|------|------|---------|
| 1 | 恒瑞医药 | A+H | A股 | 600276.SH | CNY | 2000-10-18 |
| | | | 港股 | 01276.HK | HKD | 2025-05-23 |
| 2 | 百济神州 | US+H+A | 美股 | BGNE.O | USD | 2016-02-03 |
| | | | 港股 | 06160.HK | HKD | 2018-08-08 |
| | | | A股 | 688235.SH | CNY | 2021-12-15 |
| 3 | 信达生物 | H-only | 港股 | 01801.HK | HKD | 2018-10-31 |
| 4 | 君实生物 | H+A | 港股 | 01877.HK | HKD | 2018-12-24 |
| | | | A股 | 688180.SH | CNY | 2020-07-15 |

**统计**: 4家公司, 8个上市标的, 3个市场(A股/港股/美股)

---

## 二、现有数据盘点

| 文件 | 标的 | 状态 | 说明 |
|------|------|------|------|
| `hengrui_tushare_600276.json` | 恒瑞A股 | 已有 | Tushare日线, 2025-07-04起 |
| `hengrui_hk_01276.json` | 恒瑞港股 | 已有 | 港股日线, 字段名与A股不一致 |
| `index_000933_raw.txt` | 中证医药 | 已有 | Markdown表格格式 |
| `hengrui_indicators_data.json` | 恒瑞A股 | 已有 | 含RSI/MACD/布林带/ATR/RS |
| `hengrui_indicators.html` | 恒瑞A股 | 已有 | ECharts可视化 |
| `calc_indicators.py` | 恒瑞A股 | 已有 | 指标计算脚本 |
| `calc_rs.py` | 恒瑞A股 | 已有 | RS计算脚本 |
| `gen_html.py` | 恒瑞A股 | 已有 | HTML生成脚本 |

**需要新增采集的数据**: 百济神州(3市场)、信达生物(港股)、君实生物(2市场), 共6个标的

---

## 三、工作步骤

### Phase 1: 基础设施搭建 (预计2步)

#### Step 1.1 — 创建目录结构
```
data/raw/           # 原始数据
data/standardized/  # 标准化数据
data/indicators/    # 指标数据
data/benchmark/     # 基准指数
output/html/        # 可视化页面
output/reports/     # 分析报告
scripts/collection/ # 采集脚本
scripts/processing/ # 处理脚本
scripts/visualize/  # 可视化脚本
```

#### Step 1.2 — 迁移现有数据
- 将 `hengrui_tushare_600276.json` → `data/raw/hengrui_A_600276.json`
- 将 `hengrui_hk_01276.json` → `data/raw/hengrui_HK_01276.json`
- 将 `index_000933_raw.txt` → `data/benchmark/index_000933_raw.txt`
- 将现有脚本 → `scripts/` 对应子目录

---

### Phase 2: 数据采集 (预计3步)

#### Step 2.1 — 采集A股数据
**标的**: 恒瑞(已有)、百济神州(688235.SH)、君实生物(688180.SH)  
**数据源**: Tushare `pro.daily`  
**字段**: trade_date, open, high, low, close, vol, amount, pct_chg, change, turnover  
**时间范围**: 2025-07-01 ~ 当前  
**输出**: `data/raw/{short}_A_{code}.json`

#### Step 2.2 — 采集港股数据
**标的**: 恒瑞(已有)、百济神州(06160.HK)、信达生物(01801.HK)、君实生物(01877.HK)  
**数据源**: Tushare `pro.hk_daily`  
**字段**: trade_date, open, high, low, close, volume, amount  
**时间范围**: 2025-07-01 ~ 当前  
**输出**: `data/raw/{short}_HK_{code}.json`

#### Step 2.3 — 采集美股数据
**标的**: 百济神州 (BGNE.O)  
**数据源**: Tushare `pro.us_daily`  
**字段**: trade_date, open, high, low, close, vol, amount, pct_chg, change  
**时间范围**: 2025-07-01 ~ 当前  
**输出**: `data/raw/beigene_US_BGNE.json`

> **备用方案**: 若Tushare积分不足，使用 `westock-data` Skill 采集

---

### Phase 3: 数据标准化 (预计1步)

#### Step 3.1 — 统一字段映射
对每个标的的原始数据执行:
1. 字段重命名: `vol` → `volume` (A股、美股)
2. 字段补全: 缺失字段填 `null` (如港股无 pct_chg/change)
3. 类型转换: 确保 open/high/low/close 为 float
4. 日期排序: 按 trade_date 升序
5. 去重: 同一 trade_date 仅保留一条
6. 添加 currency 字段

**输出**: `data/standardized/{short}_{market_code}_{code}_std.json`

**标准化前后对比**:
```
原始(A股):                    标准化后:
{                             {
  "trade_date": "2025-07-04",   "trade_date": "2025-07-04",
  "open": 52.61,                "open": 52.61,
  "high": 53.79,                "high": 53.79,
  "low": 52.6,                  "low": 52.6,
  "close": 53.26,               "close": 53.26,
  "vol": 477923.12,     →       "volume": 477923.12,
  "amount": 2548289.616,        "amount": 2548289.616,
  "pct_chg": 1.5056,            "pct_chg": 1.5056,
  "change": 0.79                "change": 0.79,
}                               "turnover": null,
                                "currency": "CNY"
                              }
```

---

### Phase 4: 质量校验 (预计1步)

#### Step 4.1 — 执行校验规则
按 spec 中 `quality_checks` 逐标的检查:
- [error] 日期格式 YYYY-MM-DD
- [error] 价格为正数
- [error] high >= max(open,close), low <= min(open,close)
- [error] volume >= 0
- [error] 无重复日期
- [warning] 缺失交易日标记
- [warning] 字段完整性

**输出**: `data/quality_report.json`  
**处理**: error 级问题必须修复后才能进入下一步

---

### Phase 5: 技术指标计算 (预计2步)

#### Step 5.1 — 基准指数采集
- 中证医药指数 (000933.SH): 转换 `index_000933_raw.txt` → JSON
- 恒生医疗保健指数 (HSHCI.HK): 用于港股RS计算
- 标普500医药指数: 用于美股RS计算 (可选)

**输出**: `data/benchmark/benchmark.json`

#### Step 5.2 — 计算全部技术指标
对每个标准化数据文件计算:

| 指标 | 参数 | 说明 |
|------|------|------|
| RSI | period=14 | 相对强弱 |
| MACD | 12,26,9 | DIF线/信号线/柱状图 |
| 布林带 | 20,2 | 上轨/中轨/下轨 |
| ATR | period=14 | 平均真实波幅 |
| RS | benchmark, MA20 | 相对强度(个股/基准) |
| MA | 5,10,20,60,120,250 | 均线系统 |

**复用**: 现有 `calc_indicators.py` 和 `calc_rs.py` 逻辑可泛化为通用函数  
**输出**: `data/indicators/{short}_{market_code}_{code}_indicators.json`

---

### Phase 6: 可视化生成 (预计2步)

#### Step 6.1 — 单标的指标页面
每个标的生成独立HTML, 含6个图表:
1. K线 & 成交量 (460px)
2. 布林带 (180px)
3. MACD (170px)
4. RSI (150px)
5. ATR (140px)
6. RS相对强度 (150px)

**复用**: 现有 `gen_html.py` 泛化为模板化生成  
**输出**: `output/html/{short}_{market_code}_{code}_indicators.html`

#### Step 6.2 — 多市场对比页面
对多市场上市的公司生成跨市场对比:
- 恒瑞医药: A股 vs 港股 (价格走势、溢价率、成交量对比)
- 百济神州: 美股 vs 港股 vs A股 (三市场联动分析)
- 君实生物: A股 vs 港股

**输出**: `output/html/{short}_multi_market_compare.html`

---

### Phase 7: 汇总报告 (预计1步)

#### Step 7.1 — 生成汇总报告
整合所有数据:
- 采集完成度统计
- 质量校验结果摘要
- 各标的最新指标值
- 跨市场对比要点
- 文件清单与路径索引

**输出**: `output/reports/summary_report.md`

---

## 四、执行顺序与依赖关系

```
Phase 1 (基础设施)
  │
  ├──→ Phase 2 (数据采集) ──→ Phase 3 (标准化) ──→ Phase 4 (质量校验)
  │                                                      │
  └──→ Phase 5.1 (基准指数) ──────────────────────────────┤
                                                           ▼
                                              Phase 5.2 (指标计算)
                                                           │
                                                           ▼
                                              Phase 6 (可视化)
                                                           │
                                                           ▼
                                              Phase 7 (汇总报告)
```

---

## 五、脚本复用计划

| 现有脚本 | 复用方式 | 通用化改造点 |
|---------|---------|-------------|
| `calc_indicators.py` | 提取为通用函数 | 参数化标的代码/文件路径 |
| `calc_rs.py` | 提取RS计算逻辑 | 参数化基准指数 |
| `gen_html.py` | 提取为模板引擎 | 参数化标题/数据源 |
| `fix_html.py` | 保留为调试工具 | — |

**目标**: 将硬编码的恒瑞专用脚本改造为 spec 驱动的通用脚本

---

## 六、关键注意事项

1. **Tushare积分**: 美股接口需5000+积分, 港股需2000+, 提前确认额度
2. **交易日历差异**: A股/港股/美股交易日不完全重合, 合并分析需对齐
3. **汇率影响**: 跨市场价格对比需考虑 CNY/HKD/USD 汇率换算
4. **港股字段差异**: 港股无 pct_chg/change/turnover, 标准化时填 null
5. **信达生物**: 仅港股上市, 无A股对应, 不涉及跨市场对比
6. **命名一致性**: 用户提到"信达医药", 实际公司名为"信达生物" (Innovent Biologics)
7. **API频率**: Tushare有调用频率限制, 采集间隔 ≥0.5秒
8. **数据复权**: 默认不复权(none), 如需前复权改 spec 中 adjust: qfq
