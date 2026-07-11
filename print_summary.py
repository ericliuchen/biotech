import json
import sys

OUT_DIR = "D:/AI/线上学习/data/channels"
CHANNELS_SUMMARY = f"{OUT_DIR}/_channel_summary.json"

with open(CHANNELS_SUMMARY, "r", encoding="utf-8") as f:
    summary = json.load(f)

print(f"{'='*90}")
print(f"  20日唐奇安通道 (Donchian Channel) 计算结果汇总")
print(f"  更新日期: 2026-07-11")
print(f"{'='*90}")
print(f"")
print(f"{'公司':8s} {'代码':8s} {'市场':4s} {'最新价':>8s} {'上轨':>8s} {'中轨':>8s} {'下轨':>8s} {'通道宽':>7s} {'价格位置':>8s} {'币种':6s}")
print(f"{'-'*75}")

for s in summary["stocks"]:
    pos = f"{s['price_position_pct']:.1f}%" if s["price_position_pct"] else "N/A"
    bar = "█" * int(s["price_position_pct"] / 5) if s["price_position_pct"] else ""
    arrow = "▲" if s["price_position_pct"] and s["price_position_pct"] > 65 else "▼" if s["price_position_pct"] and s["price_position_pct"] < 35 else "─"
    print(f"{s['company']:6s} {s['code']:6s} {s['market']:4s} "
          f"{s['latest_close']:>8.2f} {s['channel_upper']:>8.2f} "
          f"{s['channel_middle']:>8.2f} {s['channel_lower']:>8.2f} "
          f"{s['channel_width']:>7.2f} {pos:>8s} {s['currency']:6s}  {arrow} {bar}")

print(f"{'-'*75}")
print(f"  ▲ = 靠近上轨 (强势)  ─ = 通道中部  ▼ = 靠近下轨 (弱势)")
print(f"")
print(f"  数据文件已保存至: {OUT_DIR}/")
print(f"  共 {len(summary['stocks'])} 只股票, 周期 = {summary['period']} 日")
