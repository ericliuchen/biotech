#!/usr/bin/env python
"""
计算恒瑞医药(600276)的技术指标: RSI, MACD, 布林带, ATR
并生成ECharts可视化HTML
"""
import json
import math

# ─── 读取数据 ───
with open(r"D:\AI\线上学习\hengrui_tushare_600276.json", "r", encoding="utf-8") as f:
    raw = json.load(f)

close_prices = [d["close"] for d in raw]
high_prices = [d["high"] for d in raw]
low_prices = [d["low"] for d in raw]
dates = [d["trade_date"] for d in raw]
volumes = [d["vol"] for d in raw]

n = len(close_prices)

# ─── 1. RSI(14) ───
def calc_rsi(prices, period=14):
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    
    rsi = [None] * len(prices)
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    if avg_loss == 0:
        rsi[period] = 100.0
    else:
        rsi[period] = round(100 - 100 / (1 + avg_gain / avg_loss), 2)
    
    for i in range(period + 1, len(prices)):
        avg_gain = (avg_gain * (period - 1) + gains[i-1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i-1]) / period
        if avg_loss == 0:
            rsi[i] = 100.0
        else:
            rsi[i] = round(100 - 100 / (1 + avg_gain / avg_loss), 2)
    return rsi

rsi = calc_rsi(close_prices, 14)

# ─── 2. MACD(12, 26, 9) ───
def ema(data, period):
    result = [None] * len(data)
    k = 2 / (period + 1)
    # 初始值用 SMA
    s = sum(data[:period]) / period
    result[period-1] = s
    for i in range(period, len(data)):
        result[i] = round((data[i] - result[i-1]) * k + result[i-1], 4)
    return result

ema12 = ema(close_prices, 12)
ema26 = ema(close_prices, 26)

macd_line = [None] * n
for i in range(n):
    if ema12[i] is not None and ema26[i] is not None:
        macd_line[i] = round(ema12[i] - ema26[i], 4)

signal_line = [None] * n
# signal line is EMA of MACD line with period 9
k_signal = 2 / (9 + 1)
# Find first valid MACD index
first_valid = next(i for i in range(n) if macd_line[i] is not None)
# SMA for initial signal
valid_macds = [macd_line[i] for i in range(first_valid, first_valid + 9) if i < n and macd_line[i] is not None]
if len(valid_macds) >= 9:
    signal_line[first_valid + 8] = round(sum(valid_macds) / 9, 4)
    for i in range(first_valid + 9, n):
        signal_line[i] = round((macd_line[i] - signal_line[i-1]) * k_signal + signal_line[i-1], 4)

macd_hist = [None] * n
for i in range(n):
    if macd_line[i] is not None and signal_line[i] is not None:
        macd_hist[i] = round(macd_line[i] - signal_line[i], 4)

# ─── 3. 布林带(20, 2) ───
def sma(data, period):
    result = [None] * len(data)
    for i in range(period - 1, len(data)):
        result[i] = sum(data[i - period + 1:i + 1]) / period
    return result

def stddev(data, period):
    result = [None] * len(data)
    for i in range(period - 1, len(data)):
        mean = sum(data[i - period + 1:i + 1]) / period
        variance = sum((x - mean) ** 2 for x in data[i - period + 1:i + 1]) / period
        result[i] = math.sqrt(variance)
    return result

bb_middle = sma(close_prices, 20)
bb_std = stddev(close_prices, 20)
bb_upper = [None] * n
bb_lower = [None] * n
for i in range(n):
    if bb_middle[i] is not None and bb_std[i] is not None:
        bb_upper[i] = round(bb_middle[i] + 2 * bb_std[i], 2)
        bb_lower[i] = round(bb_middle[i] - 2 * bb_std[i], 2)
    if bb_middle[i] is not None:
        bb_middle[i] = round(bb_middle[i], 2)

# ─── 4. ATR(14) ───
def calc_tr(high, low, prev_close):
    """计算单日 True Range"""
    return max(high - low, abs(high - prev_close), abs(low - prev_close))

tr_values = [None] * n
for i in range(1, n):
    tr_values[i] = round(calc_tr(high_prices[i], low_prices[i], close_prices[i-1]), 4)

def wilder_ema(data, period):
    """Wilder's smoothed EMA (initial = SMA, then smoothing)"""
    result = [None] * len(data)
    # 找到第一个非 None 值的索引
    first = next(i for i in range(len(data)) if data[i] is not None)
    # 初始值用 SMA
    valid = [data[i] for i in range(first, first + period) if i < len(data) and data[i] is not None]
    if len(valid) >= period:
        result[first + period - 1] = sum(valid) / period
        k = 1 / period
        for i in range(first + period, len(data)):
            if data[i] is not None:
                result[i] = round((data[i] - result[i-1]) * k + result[i-1], 4)
    return result

atr = wilder_ema(tr_values, 14)

# ─── 输出结果预览 ───
print(f"{'日期':<12} {'收盘':>6} {'RSI(14)':>8} {'MACD':>8} {'信号':>8} {'柱状':>8} {'上轨':>8} {'中轨':>8} {'下轨':>8} {'ATR':>8}")
print("=" * 96)
for i in range(n):
    if rsi[i] is not None:
        r = f"{rsi[i]:>8.2f}"
    else:
        r = "      -"
    
    if macd_line[i] is not None:
        m = f"{macd_line[i]:>8.4f}"
    else:
        m = "      -"
    
    if signal_line[i] is not None:
        s = f"{signal_line[i]:>8.4f}"
    else:
        s = "      -"
    
    if macd_hist[i] is not None:
        h = f"{macd_hist[i]:>8.4f}"
    else:
        h = "      -"
    
    if bb_upper[i] is not None:
        bu = f"{bb_upper[i]:>8.2f}"
        bm = f"{bb_middle[i]:>8.2f}"
        bl = f"{bb_lower[i]:>8.2f}"
    else:
        bu = "      -"
        bm = "      -"
        bl = "      -"
    
    if atr[i] is not None:
        a = f"{atr[i]:>8.4f}"
    else:
        a = "      -"
    
    print(f"{dates[i]:<12} {close_prices[i]:>6.2f} {r} {m} {s} {h} {bu} {bm} {bl} {a}")

# ─── 生成数据JSON给HTML ───
output_data = []
for i in range(n):
    output_data.append({
        "date": dates[i],
        "open": raw[i]["open"],
        "high": raw[i]["high"],
        "low": raw[i]["low"],
        "close": close_prices[i],
        "vol": volumes[i],
        "rsi": rsi[i],
        "macd": macd_line[i],
        "signal": signal_line[i],
        "hist": macd_hist[i],
        "bb_upper": bb_upper[i],
        "bb_mid": bb_middle[i],
        "bb_lower": bb_lower[i],
        "atr": atr[i]
    })

with open(r"D:\AI\线上学习\hengrui_indicators_data.json", "w", encoding="utf-8") as f:
    json.dump(output_data, f, ensure_ascii=False, indent=2)

print(f"\n共 {n} 条记录")
print("数据已保存至 hengrui_indicators_data.json")
