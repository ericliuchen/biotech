#!/usr/bin/env python
"""
计算恒瑞医药(600276)的相对强度指标 RS = 股价 / 中证医药指数(000933)
并更新HTML可视化
"""
import json, math, re
from datetime import datetime

# ─── 1. 读取恒瑞股价数据 ───
with open(r"D:\AI\线上学习\hengrui_tushare_600276.json", "r", encoding="utf-8") as f:
    hengrui_raw = json.load(f)

# ─── 2. 读取中证医药指数数据 ───
with open(r"D:\AI\线上学习\index_000933_raw.txt", "r", encoding="utf-8") as f:
    text = f.read()

# 解析markdown表格
lines = text.strip().split("\n")
# 找分隔行后的数据行
idx_data = []
started = False
for line in lines:
    if line.startswith("| ---"):
        started = True
        continue
    if started and line.startswith("|"):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 8:
            try:
                idx_data.append({
                    "date": parts[1],
                    "close": float(parts[3].replace(",", ""))
                })
            except:
                pass

# 按日期排序
idx_data.sort(key=lambda x: x["date"])

# 构建索引映射 {date: close}
idx_map = {d["date"]: d["close"] for d in idx_data}

# ─── 3. 构建恒瑞数据映射 ───
hengrrui_map = {d["trade_date"]: d for d in hengrui_raw}

# ─── 4. 合并数据（按恒瑞交易日对齐） ───
combined = []
for d in hengrui_raw:
    date = d["trade_date"]
    idx_close = idx_map.get(date)
    if idx_close is not None:
        rs = round(d["close"] / idx_close, 6)
        combined.append({
            "date": date,
            "close": d["close"],
            "idx_close": idx_close,
            "rs": rs
        })

print(f"对齐交易日数: {len(combined)}")

# 计算RS的20日均线
rs_values = [c["rs"] for c in combined]
rs_ma20 = [None] * len(rs_values)
for i in range(19, len(rs_values)):
    rs_ma20[i] = round(sum(rs_values[i-19:i+1]) / 20, 6)

# 输出最近10行
print(f"\n{'日期':<12} {'恒瑞收盘':>8} {'指数收盘':>10} {'RS':>10} {'RS_MA20':>10}")
print("=" * 52)
for i in range(max(0, len(combined)-10), len(combined)):
    c = combined[i]
    ma = rs_ma20[i] if rs_ma20[i] else ""
    print(f"{c['date']:<12} {c['close']:>8.2f} {c['idx_close']:>10.2f} {c['rs']:>10.6f} {f'{ma:.6f}' if ma else '':>10}")

# ─── 5. 保存合并数据 ───
# 重新读取旧的完整指标数据
with open(r"D:\AI\线上学习\hengrui_indicators_data.json", "r", encoding="utf-8") as f:
    old_data = json.load(f)

# 给每条数据加上RS字段
combo_dict = {c["date"]: c for c in combined}
for item in old_data:
    date = item["date"]
    if date in combo_dict:
        item["rs"] = combo_dict[date]["rs"]
        item["idx_close"] = combo_dict[date]["idx_close"]
        # 找对应的RS_MA20
        idx = next(i for i, c in enumerate(combined) if c["date"] == date)
        item["rs_ma20"] = rs_ma20[idx] if rs_ma20[idx] is not None else None
    else:
        item["rs"] = None
        item["idx_close"] = None
        item["rs_ma20"] = None

with open(r"D:\AI\线上学习\hengrui_indicators_data.json", "w", encoding="utf-8") as f:
    json.dump(old_data, f, ensure_ascii=False, indent=2)

print(f"\n数据已保存至 hengrui_indicators_data.json (含RS字段)")
print(f"共 {len(old_data)} 条记录，其中 {len(combined)} 条有RS数据")
