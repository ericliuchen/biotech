import json
from pathlib import Path

STD_DIR = Path("D:/AI/线上学习/data/standardized")
OUT_DIR = Path("D:/AI/线上学习/data/atr")
OUT_DIR.mkdir(parents=True, exist_ok=True)

ATR_PERIOD = 20  # 海龟策略标准参数

STOCK_MAP = {
    "hengrui_A_600276_std.json":      ("恒瑞医药", "600276", "A股"),
    "hengrui_HK_01276_std.json":      ("恒瑞医药", "01276",  "港股"),
    "beigene_A_688235_std.json":      ("百济神州", "688235", "A股"),
    "beigene_HK_06160_std.json":      ("百济神州", "06160",  "港股"),
    "beigene_US_ONC_std.json":        ("百济神州", "ONC",    "美股"),
    "innovent_HK_01801_std.json":     ("信达生物", "01801",  "港股"),
    "junshi_A_688180_std.json":       ("君实生物", "688180", "A股"),
    "junshi_HK_01877_std.json":       ("君实生物", "01877",  "港股"),
}


def calc_true_range(prev_close, high, low):
    """单日 True Range = max(H-L, |H-PC|, |L-PC|)"""
    hl = high - low
    hpc = abs(high - prev_close)
    lpc = abs(low - prev_close)
    return max(hl, hpc, lpc)


def calc_atr(data, period=ATR_PERIOD):
    """计算 ATR，返回带 ATR 的数据列表"""
    result = []
    tr_list = []

    for i, d in enumerate(data):
        tr = None
        atr = None

        if i == 0:
            # 第一天没有前收价，用 H-L 作为 TR 近似
            tr = d["high"] - d["low"]
        else:
            tr = calc_true_range(data[i - 1]["close"], d["high"], d["low"])

        if tr is not None:
            tr_list.append(tr)

        # 计算 ATR
        if len(tr_list) >= period:
            # Wilder 平滑法（更常用）：ATR = (之前ATR * (period-1) + 当前TR) / period
            if len(tr_list) == period:
                # 第一个 ATR = 前 period 个 TR 的简单平均
                atr = sum(tr_list[-period:]) / period
            else:
                # 后续 ATR 用 Wilder 平滑
                atr = (result[-1]["atr"] * (period - 1) + tr) / period
        elif len(tr_list) > 0:
            # 数据不足 period 时，用已有数据计算简单平均
            atr = sum(tr_list) / len(tr_list)

        entry = {
            "trade_date": d["trade_date"],
            "open": d["open"],
            "high": d["high"],
            "low": d["low"],
            "close": d["close"],
            "volume": d.get("volume", 0),
            "currency": d.get("currency", ""),
            "true_range": round(tr, 4) if tr is not None else None,
            "atr": round(atr, 4) if atr is not None else None,
        }
        result.append(entry)

    return result


all_summaries = []

for fname, (company, code, market) in STOCK_MAP.items():
    filepath = STD_DIR / fname
    with open(filepath, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    raw_data.sort(key=lambda x: x["trade_date"])

    atr_data = calc_atr(raw_data)

    out_name = fname.replace("_std.json", "_atr.json")
    out_path = OUT_DIR / out_name
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(atr_data, f, ensure_ascii=False, indent=2)

    # 提取最新数据
    latest = atr_data[-1]
    # 找到第一个有效的 ATR
    valid_atr = [d for d in atr_data if d["atr"] is not None]

    summary = {
        "company": company,
        "code": code,
        "market": market,
        "file": out_name,
        "total_records": len(atr_data),
        "latest_date": latest["trade_date"],
        "latest_close": latest["close"],
        "latest_tr": latest["true_range"],
        "latest_atr": latest["atr"],
        "atr_pct": round(latest["atr"] / latest["close"] * 100, 2) if latest["atr"] and latest["close"] else None,
        "atr_trend_20": None,  # 后续可计算趋势
        "currency": latest["currency"],
    }

    # 计算 ATR 变化趋势（对比 5 天前后）
    if len(valid_atr) >= 25:
        atr_now = valid_atr[-1]["atr"]
        atr_5ago = valid_atr[-6]["atr"] if len(valid_atr) >= 6 else atr_now
        summary["atr_change_5d_pct"] = round((atr_now - atr_5ago) / atr_5ago * 100, 1)
        summary["atr_trend"] = "上升" if atr_now > atr_5ago * 1.05 else "下降" if atr_now < atr_5ago * 0.95 else "平稳"
    else:
        summary["atr_change_5d_pct"] = None
        summary["atr_trend"] = "数据不足"

    all_summaries.append(summary)

    print(f"  {company:6s} ({code:6s} {market:4s})  "
          f"收盘={latest['close']:>8.2f}  "
          f"TR={latest['true_range']:>8.4f}  "
          f"ATR({ATR_PERIOD})={latest['atr']:>8.4f}  "
          f"ATR%={summary['atr_pct']:>5.2f}%  "
          f"趋势={summary['atr_trend']}  ({summary['atr_change_5d_pct']:+.1f}%)")

# 保存汇总
SUMMARY_FILE = OUT_DIR / "_atr_summary.json"
with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
    json.dump({
        "period": ATR_PERIOD,
        "method": "Wilder_smoothing",
        "stocks": all_summaries,
        "generated": "2026-07-11"
    }, f, ensure_ascii=False, indent=2)

print(f"\n共处理 {len(all_summaries)} 只标的")
print(f"数据保存至: {OUT_DIR}")
print(f"汇总文件: {SUMMARY_FILE}")
