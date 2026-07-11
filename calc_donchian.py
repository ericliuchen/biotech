import json
import os
from pathlib import Path

STD_DIR = Path("D:/AI/线上学习/data/standardized")
OUT_DIR = Path("D:/AI/线上学习/data/channels")
OUT_DIR.mkdir(parents=True, exist_ok=True)

PERIOD = 20

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

SUMMARY_FILE = OUT_DIR / "_channel_summary.json"

def calc_donchian(data, period=PERIOD):
    """计算唐奇安通道，返回带通道的数据列表"""
    result = []
    for i in range(len(data)):
        if i < period - 1:
            upper = None
            lower = None
            middle = None
        else:
            window = data[i - period + 1 : i + 1]
            highs = [d["high"] for d in window]
            lows = [d["low"] for d in window]
            upper = max(highs)
            lower = min(lows)
            middle = (upper + lower) / 2

        entry = {
            "trade_date": data[i]["trade_date"],
            "close": data[i]["close"],
            "high": data[i]["high"],
            "low": data[i]["low"],
            "volume": data[i].get("volume", 0),
            "currency": data[i].get("currency", ""),
            "channel_upper": round(upper, 2) if upper is not None else None,
            "channel_middle": round(middle, 2) if middle is not None else None,
            "channel_lower": round(lower, 2) if lower is not None else None,
        }
        result.append(entry)
    return result


all_summaries = []

for fname, (company, code, market) in STOCK_MAP.items():
    filepath = STD_DIR / fname
    with open(filepath, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # 按日期升序排列
    raw_data.sort(key=lambda x: x["trade_date"])

    channel_data = calc_donchian(raw_data)

    # 保存通道数据
    out_name = fname.replace("_std.json", "_channel.json")
    out_path = OUT_DIR / out_name
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(channel_data, f, ensure_ascii=False, indent=2)

    # 提取最新一条有效的通道数据
    valid = [d for d in channel_data if d["channel_upper"] is not None]
    latest = valid[-1] if valid else channel_data[-1]

    summary = {
        "company": company,
        "code": code,
        "market": market,
        "file": out_name,
        "total_records": len(channel_data),
        "latest_date": latest["trade_date"],
        "latest_close": latest["close"],
        "channel_upper": latest["channel_upper"],
        "channel_middle": latest["channel_middle"],
        "channel_lower": latest["channel_lower"],
        "channel_width": round(latest["channel_upper"] - latest["channel_lower"], 2),
        "price_position_pct": round(
            (latest["close"] - latest["channel_lower"])
            / max(latest["channel_upper"] - latest["channel_lower"], 0.001)
            * 100,
            1
        ) if latest["channel_upper"] else None,
        "currency": latest["currency"],
    }
    all_summaries.append(summary)

    print(f"  {company:6s} ({code:6s} {market})  "
          f"上轨={latest['channel_upper']:>8.2f}  "
          f"中轨={latest['channel_middle']:>8.2f}  "
          f"下轨={latest['channel_lower']:>8.2f}  "
          f"宽度={summary['channel_width']:>6.2f}  "
          f"价格位置={summary['price_position_pct']:>5.1f}%")

# 保存汇总
with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
    json.dump({"period": PERIOD, "stocks": all_summaries, "generated": "2026-07-11"}, f, ensure_ascii=False, indent=2)

print(f"\n共处理 {len(all_summaries)} 只股票，结果已保存至 {OUT_DIR}")
print(f"汇总文件: {SUMMARY_FILE}")
