#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
采集8个标的的日K数据并计算 MA(5) / MA(15) 均线
数据源: westock-data (腾讯自选股)
输出: data/indicators/ma_data.json + 各标的标准化JSON
"""
import json
import subprocess
import os
import sys

# ─── 配置 ───
NODE_EXE = r"C:\Users\ericl\.workbuddy\binaries\node\versions\22.22.2\node.exe"
WESTOCK_SCRIPT = r"D:\新建文件夹 (2)\WorkBuddy\resources\app.asar.unpacked\resources\builtin-skills\westock-data\scripts\index.js"

BASE_DIR = r"D:\AI\线上学习"
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
STD_DIR = os.path.join(BASE_DIR, "data", "standardized")
IND_DIR = os.path.join(BASE_DIR, "data", "indicators")

START_DATE = "2025-07-01"
END_DATE = "2026-07-11"

SHORT_MA = 5    # 短均线周期
LONG_MA = 15    # 长均线周期

# ─── 8个标的清单 ───
STOCKS = [
    {"name": "恒瑞医药", "market": "A股", "code": "600276", "westock_code": "sh600276", "short": "hengrui",   "mkt_code": "A",  "currency": "CNY"},
    {"name": "恒瑞医药", "market": "港股", "code": "01276", "westock_code": "hk01276", "short": "hengrui",   "mkt_code": "HK", "currency": "HKD"},
    {"name": "百济神州", "market": "美股", "code": "ONC",   "westock_code": "usONC.OQ",  "short": "beigene",  "mkt_code": "US", "currency": "USD"},
    {"name": "百济神州", "market": "港股", "code": "06160", "westock_code": "hk06160", "short": "beigene",  "mkt_code": "HK", "currency": "HKD"},
    {"name": "百济神州", "market": "A股", "code": "688235", "westock_code": "sh688235", "short": "beigene",  "mkt_code": "A",  "currency": "CNY"},
    {"name": "信达生物", "market": "港股", "code": "01801", "westock_code": "hk01801", "short": "innovent", "mkt_code": "HK", "currency": "HKD"},
    {"name": "君实生物", "market": "港股", "code": "01877", "westock_code": "hk01877", "short": "junshi",    "mkt_code": "HK", "currency": "HKD"},
    {"name": "君实生物", "market": "A股", "code": "688180", "westock_code": "sh688180", "short": "junshi",    "mkt_code": "A",  "currency": "CNY"},
]


def fetch_kline(westock_code, start, end, retries=3):
    """调用 westock-data kline 获取日K数据，返回列表(按日期升序)。带重试。"""
    import time
    cmd = [NODE_EXE, WESTOCK_SCRIPT, "kline", westock_code, "--start", start, "--end", end]
    
    for attempt in range(retries):
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, encoding="utf-8")
        
        if result.returncode != 0:
            print(f"  [WARN] 第{attempt+1}次尝试失败: {result.stderr[:200]}")
            time.sleep(1)
            continue
        
        # 解析 markdown 表格
        lines = result.stdout.strip().split("\n")
        if "数据为空" in result.stdout or len(lines) < 4:
            print(f"  [WARN] 第{attempt+1}次返回空数据，重试中...")
            time.sleep(1.5)
            continue
        break
    else:
        print(f"  [ERROR] {retries}次重试后仍无数据")
        return []
    
    # 解析 markdown 表格 (成功时)
    lines = result.stdout.strip().split("\n")
    records = []
    header_seen = False
    for line in lines:
        line = line.strip()
        if not line or not line.startswith("|"):
            continue
        if line.startswith("| date"):
            header_seen = True
            continue
        if line.startswith("| ---"):
            continue
        if not header_seen:
            continue
        
        parts = [p.strip() for p in line.split("|")]
        # parts: ['', date, open, last, high, low, volume, amount, exchange, '']
        if len(parts) < 9:
            continue
        
        try:
            rec = {
                "trade_date": parts[1],
                "open":       float(parts[2]),
                "close":      float(parts[3]),   # last → close
                "high":       float(parts[4]),
                "low":        float(parts[5]),
                "volume":     float(parts[6]),
                "amount":     float(parts[7]),
            }
            records.append(rec)
        except (ValueError, IndexError) as e:
            print(f"  [WARN] 解析跳过行: {line[:80]} ({e})")
            continue
    
    # westock-data 返回最新在前，反转为升序
    records.reverse()
    return records


def calc_sma(prices, period):
    """计算简单移动平均线 SMA"""
    result = [None] * len(prices)
    for i in range(period - 1, len(prices)):
        result[i] = round(sum(prices[i - period + 1 : i + 1]) / period, 4)
    return result


def calc_ma_crossover(short_ma, long_ma):
    """判断均线交叉信号"""
    signals = [""] * len(short_ma)
    for i in range(1, len(short_ma)):
        if short_ma[i] is None or long_ma[i] is None:
            continue
        if short_ma[i-1] is None or long_ma[i-1] is None:
            continue
        prev_diff = short_ma[i-1] - long_ma[i-1]
        curr_diff = short_ma[i] - long_ma[i]
        if prev_diff <= 0 and curr_diff > 0:
            signals[i] = "金叉"
        elif prev_diff >= 0 and curr_diff < 0:
            signals[i] = "死叉"
    return signals


def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(STD_DIR, exist_ok=True)
    os.makedirs(IND_DIR, exist_ok=True)
    
    all_results = []
    
    for stock in STOCKS:
        label = f"{stock['name']}({stock['market']})"
        print(f"\n{'='*60}")
        print(f"采集: {label}  代码: {stock['westock_code']}")
        print(f"{'='*60}")
        
        # 1. 采集K线
        records = fetch_kline(stock["westock_code"], START_DATE, END_DATE)
        if not records:
            print(f"  [SKIP] {label} 无数据，跳过")
            continue
        print(f"  获取 {len(records)} 条日线数据 ({records[0]['trade_date']} ~ {records[-1]['trade_date']})")
        
        # 2. 保存原始数据
        raw_filename = f"{stock['short']}_{stock['mkt_code']}_{stock['code']}.json"
        raw_path = os.path.join(RAW_DIR, raw_filename)
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        print(f"  原始数据 → {raw_path}")
        
        # 3. 标准化 + 添加货币
        std_records = []
        for r in records:
            std_rec = dict(r)
            std_rec["currency"] = stock["currency"]
            std_records.append(std_rec)
        
        std_filename = f"{stock['short']}_{stock['mkt_code']}_{stock['code']}_std.json"
        std_path = os.path.join(STD_DIR, std_filename)
        with open(std_path, "w", encoding="utf-8") as f:
            json.dump(std_records, f, ensure_ascii=False, indent=2)
        print(f"  标准化  → {std_path}")
        
        # 4. 计算 MA(5) 和 MA(15)
        closes = [r["close"] for r in std_records]
        ma_short = calc_sma(closes, SHORT_MA)
        ma_long = calc_sma(closes, LONG_MA)
        signals = calc_ma_crossover(ma_short, ma_long)
        
        # 5. 构建指标数据
        indicator_records = []
        for i, r in enumerate(std_records):
            indicator_records.append({
                "trade_date": r["trade_date"],
                "open":       r["open"],
                "high":       r["high"],
                "low":        r["low"],
                "close":      r["close"],
                "volume":     r["volume"],
                "amount":     r.get("amount"),
                "currency":   r["currency"],
                f"ma{SHORT_MA}":  ma_short[i],
                f"ma{LONG_MA}":   ma_long[i],
                "ma_signal":  signals[i],
            })
        
        ind_filename = f"{stock['short']}_{stock['mkt_code']}_{stock['code']}_ma.json"
        ind_path = os.path.join(IND_DIR, ind_filename)
        with open(ind_path, "w", encoding="utf-8") as f:
            json.dump(indicator_records, f, ensure_ascii=False, indent=2)
        print(f"  MA指标  → {ind_path}")
        
        # 6. 统计摘要
        valid_short = [x for x in ma_short if x is not None]
        valid_long = [x for x in ma_long if x is not None]
        golden_cross = signals.count("金叉")
        death_cross = signals.count("死叉")
        latest_close = closes[-1] if closes else None
        latest_ma5 = ma_short[-1] if ma_short else None
        latest_ma15 = ma_long[-1] if ma_long else None
        
        # 判断当前均线状态
        if latest_ma5 is not None and latest_ma15 is not None:
            if latest_ma5 > latest_ma15:
                ma_status = "多头排列 (MA5 > MA15)"
            elif latest_ma5 < latest_ma15:
                ma_status = "空头排列 (MA5 < MA15)"
            else:
                ma_status = "均线粘合"
        else:
            ma_status = "数据不足"
        
        summary = {
            "name":          stock["name"],
            "market":        stock["market"],
            "code":          stock["code"],
            "westock_code":  stock["westock_code"],
            "currency":      stock["currency"],
            "data_count":    len(records),
            "date_range":    f"{records[0]['trade_date']} ~ {records[-1]['trade_date']}",
            "latest_close":  latest_close,
            f"latest_ma{SHORT_MA}": latest_ma5,
            f"latest_ma{LONG_MA}":  latest_ma15,
            "ma_status":     ma_status,
            "golden_cross":  golden_cross,
            "death_cross":   death_cross,
            "ma_short_period": SHORT_MA,
            "ma_long_period":  LONG_MA,
            "file_raw":         raw_filename,
            "file_std":         std_filename,
            "file_indicators":  ind_filename,
        }
        all_results.append(summary)
        
        print(f"  ── 摘要 ──")
        print(f"  最新收盘: {latest_close} {stock['currency']}")
        print(f"  MA{SHORT_MA}: {latest_ma5}  MA{LONG_MA}: {latest_ma15}")
        print(f"  均线状态: {ma_status}")
        print(f"  金叉 {golden_cross} 次, 死叉 {death_cross} 次")
    
    # ─── 汇总输出 ───
    summary_path = os.path.join(IND_DIR, "ma_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "meta": {
                "description": "8个标的 MA(5)/MA(15) 均线数据汇总",
                "short_ma": SHORT_MA,
                "long_ma": LONG_MA,
                "start_date": START_DATE,
                "end_date": END_DATE,
                "data_source": "westock-data (腾讯自选股)",
                "generated": "2026-07-11",
            },
            "stocks": all_results,
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"汇总报告 → {summary_path}")
    print(f"共处理 {len(all_results)} 个标的")
    print(f"{'='*60}")
    
    # 打印汇总表
    print(f"\n{'标的':<16} {'市场':<6} {'最新收盘':>10} {'MA5':>10} {'MA15':>10} {'状态':<20} {'金叉':>4} {'死叉':>4}")
    print("-" * 90)
    for s in all_results:
        print(f"{s['name']:<16} {s['market']:<6} {s['latest_close']:>10.2f} {s[f'latest_ma{SHORT_MA}']:>10.2f} {s[f'latest_ma{LONG_MA}']:>10.2f} {s['ma_status']:<20} {s['golden_cross']:>4} {s['death_cross']:>4}")


if __name__ == "__main__":
    main()
