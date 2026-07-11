import json, sys, io, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from pathlib import Path

STD_DIR = Path("D:/AI/线上学习/data/standardized")
OUT_DIR = Path("D:/AI/线上学习/data/backtest30")
OUT_DIR.mkdir(parents=True, exist_ok=True)

PERIOD = 30  # 通道周期
EXIT_PERIOD = 15  # 出场通道周期 (2:1 比例)

STOCK_MAP = {
    "hengrui_A_600276_std.json":      ("恒瑞医药", "600276", "A股", "CNY"),
    "hengrui_HK_01276_std.json":      ("恒瑞医药", "01276",  "港股", "HKD"),
    "beigene_A_688235_std.json":      ("百济神州", "688235", "A股", "CNY"),
    "beigene_HK_06160_std.json":      ("百济神州", "06160",  "港股", "HKD"),
    "beigene_US_ONC_std.json":        ("百济神州", "ONC",    "美股", "USD"),
    "innovent_HK_01801_std.json":     ("信达生物", "01801",  "港股", "HKD"),
    "junshi_A_688180_std.json":       ("君实生物", "688180", "A股", "CNY"),
    "junshi_HK_01877_std.json":       ("君实生物", "01877",  "港股", "HKD"),
}

# ============================================================
# 1. 计算指标
# ============================================================
def calc_atr_wilder(data, period=20):
    tr_list, atr_list = [], []
    for i, d in enumerate(data):
        if i == 0:
            tr = d["high"] - d["low"]
        else:
            hl = d["high"] - d["low"]
            hpc = abs(d["high"] - data[i-1]["close"])
            lpc = abs(d["low"] - data[i-1]["close"])
            tr = max(hl, hpc, lpc)
        tr_list.append(tr)
        if len(tr_list) == period:
            atr = sum(tr_list) / period
        elif len(tr_list) > period:
            atr = (atr_list[-1] * (period - 1) + tr) / period
        else:
            atr = sum(tr_list) / len(tr_list)
        atr_list.append(atr)
    return atr_list

def gen_signals(data, entry_period, exit_period):
    """生成信号：入场=entry_period日通道，出场=exit_period日通道"""
    n = len(data)
    atr_list = calc_atr_wilder(data, 20)
    signals = []
    position = False
    pos_type = None
    entry_price = 0
    entry_date = ""
    add_count = 0
    stop_price = 0
    highest_since_entry = 0
    lowest_since_entry = float('inf')
    trades = []

    for i in range(n):
        d = data[i]
        date = d["trade_date"]
        close = d["close"]
        high = d["high"]
        low = d["low"]
        atr = atr_list[i]

        # Entry channel (前period天历史数据)
        if i >= entry_period:
            prev_high = max(data[j]["high"] for j in range(i-entry_period, i))
            prev_low  = min(data[j]["low"] for j in range(i-entry_period, i))
        else:
            prev_high = None; prev_low = None

        # Exit channel
        if i >= exit_period:
            prev_exit_high = max(data[j]["high"] for j in range(i-exit_period, i))
            prev_exit_low  = min(data[j]["low"] for j in range(i-exit_period, i))
        else:
            prev_exit_high = None; prev_exit_low = None

        sig = {
            "trade_date": date, "close": close, "high": high, "low": low,
            "volume": d.get("volume",0), "currency": d.get("currency",""),
            "atr": round(atr,4),
            f"prev{entry_period}_high": round(prev_high,2) if prev_high else None,
            f"prev{entry_period}_low": round(prev_low,2) if prev_low else None,
            f"prev{exit_period}_high": round(prev_exit_high,2) if prev_exit_high else None,
            f"prev{exit_period}_low": round(prev_exit_low,2) if prev_exit_low else None,
            "entry_signal": False, "exit_signal": False, "add_signal": False,
            "signal_type": None, "signal_price": None, "stop_loss": None,
            "position": False,
        }

        # === 持仓管理 ===
        if position:
            if pos_type == "long":
                highest_since_entry = max(highest_since_entry, high)
            else:
                lowest_since_entry = min(lowest_since_entry, low)

            exited = False
            # 第1层：2ATR
            if pos_type == "long" and low <= stop_price:
                sig["exit_signal"] = True; sig["signal_type"] = "止损出场 (2ATR)"; exited = True
                reason = "止损 (2ATR)"
            elif pos_type == "short" and high >= stop_price:
                sig["exit_signal"] = True; sig["signal_type"] = "止损出场 (2ATR)"; exited = True
                reason = "止损 (2ATR)"
            # 第2层：反向突破exit_period通道
            elif pos_type == "long" and low <= prev_exit_low:
                sig["exit_signal"] = True; sig["signal_type"] = f"出场 (跌破{exit_period}日低点)"; exited = True
                reason = f"趋势反转 ({exit_period}日通道)"
            elif pos_type == "short" and high >= prev_exit_high:
                sig["exit_signal"] = True; sig["signal_type"] = f"出场 (突破{exit_period}日高点)"; exited = True
                reason = f"趋势反转 ({exit_period}日通道)"

            if exited:
                pnl = (close - entry_price) * (1 if pos_type=="long" else -1)
                pnl_pct = pnl / entry_price * 100
                trades.append({
                    "entry_date": entry_date, "exit_date": date,
                    "position_type": pos_type, "entry_price": round(entry_price,2),
                    "exit_price": round(close,2), "pnl_pct": round(pnl_pct,2),
                    "reason": reason, "add_count": add_count,
                })
                position = False; pos_type = None; entry_price = 0
                entry_date = ""; add_count = 0; stop_price = 0
                highest_since_entry = 0; lowest_since_entry = float('inf')
            else:
                # 第3层：浮盈保护
                if pos_type == "long" and highest_since_entry >= entry_price + 10 * atr:
                    if stop_price < entry_price: stop_price = entry_price
                elif pos_type == "short" and lowest_since_entry <= entry_price - 10 * atr:
                    if stop_price > entry_price: stop_price = entry_price
                # 加仓
                if pos_type == "long" and add_count < 4:
                    next_add = entry_price + (add_count + 1) * 0.5 * atr
                    if close >= next_add:
                        sig["add_signal"] = True; add_count += 1
                        sig["signal_type"] = f"加仓 第{add_count}次"
                        sig["signal_price"] = round(next_add,2)

        # === 入场 ===
        if not position and prev_high is not None and prev_low is not None:
            if close > prev_high:
                sig["entry_signal"] = True
                sig["signal_type"] = f"做多入场 (突破{entry_period}日高点)"
                sig["signal_price"] = round(close,2)
                position = True; pos_type = "long"
                entry_price = close; entry_date = date; add_count = 0
                stop_price = entry_price - 2 * atr
                highest_since_entry = high; lowest_since_entry = float('inf')
            elif close < prev_low:
                sig["entry_signal"] = True
                sig["signal_type"] = f"做空入场 (跌破{entry_period}日低点)"
                sig["signal_price"] = round(close,2)
                position = True; pos_type = "short"
                entry_price = close; entry_date = date; add_count = 0
                stop_price = entry_price + 2 * atr
                highest_since_entry = 0; lowest_since_entry = low

        if position: sig["stop_loss"] = round(stop_price,2)
        sig["position"] = position
        signals.append(sig)

    return signals, trades


# ============================================================
# 2. 回测
# ============================================================
def run_backtest(signals, initial_capital=1000000):
    capital = initial_capital
    qty = 0; ptype = None; entry_p = 0; entry_d = ""
    add_c = 0; stop_p = 0; peak = capital; max_dd = 0
    trade_c = 0; win_c = 0; loss_c = 0; total_pnl = 0
    equity_curve = []; trade_records = []; dd_curve = []

    for i, d in enumerate(signals):
        close = d["close"]
        atr = d["atr"] or 1
        date = d["trade_date"]
        entry_sig = d.get("entry_signal", False)
        exit_sig = d.get("exit_signal", False)
        add_sig = d.get("add_signal", False)
        sig_type = d.get("signal_type", "")

        # Exit
        if qty != 0 and exit_sig:
            pnl = (close - entry_p) * qty * (1 if ptype=="long" else -1)
            pnl_pct = pnl / capital * 100
            total_pnl += pnl; capital += pnl
            trade_records.append({
                "entry_date": entry_d, "exit_date": date,
                "position_type": ptype, "entry_price": round(entry_p,2),
                "exit_price": round(close,2), "qty": qty,
                "pnl": round(pnl,2), "pnl_pct": round(pnl_pct,2),
                "reason": sig_type, "add_count": add_c,
            })
            if pnl > 0: win_c += 1
            else: loss_c += 1
            trade_c += 1
            qty = 0; ptype = None; add_c = 0

        # Entry
        if qty == 0 and entry_sig:
            if "做多" in str(sig_type): ptype = "long"
            elif "做空" in str(sig_type): ptype = "short"
            entry_p = close; entry_d = date; add_c = 0
            risk_per = 2 * atr
            share = max(100, round((capital * 0.01) / risk_per / 100) * 100)
            qty = int(share)
            stop_p = close - 2 * atr if ptype == "long" else close + 2 * atr

        # Add
        elif qty != 0 and add_sig and add_c < 4:
            add_c += 1
            add_qty = max(100, int(qty / 2)) if add_c == 1 else max(100, int(qty / (2*add_c+1)))
            entry_p = (entry_p * qty + close * add_qty) / (qty + add_qty)
            qty += add_qty

        # Equity
        if qty != 0:
            upnl = (close - entry_p) * qty * (1 if ptype=="long" else -1)
            nv = capital + upnl
        else:
            nv = capital
        equity_curve.append({"date": date, "net_value": round(nv,2)})
        if nv > peak: peak = nv
        dd = (peak - nv) / peak * 100
        dd_curve.append({"date": date, "dd": round(dd,2)})
        if dd > max_dd: max_dd = dd

    return {
        "equity_curve": equity_curve, "trades": trade_records, "dd_curve": dd_curve,
        "final_capital": round(capital,2), "total_pnl": round(total_pnl,2),
        "total_return": round((capital-initial_capital)/initial_capital*100,2),
        "max_dd": round(max_dd,2), "trade_count": trade_c,
        "win_count": win_c, "loss_count": loss_c,
    }


# ============================================================
# 3. 运行
# ============================================================
all_results = []
stats_list = []

for fname, (name, code, market, ccy) in STOCK_MAP.items():
    with open(STD_DIR / fname, "r", encoding="utf-8") as f:
        raw = json.load(f)
    raw.sort(key=lambda x: x["trade_date"])

    # 信号 + 回测
    signals, trades = gen_signals(raw, PERIOD, EXIT_PERIOD)
    bt = run_backtest(signals)

    # 保存
    out_tag = f"{name}_{code}"
    with open(OUT_DIR / f"{out_tag}_signals30.json", "w", encoding="utf-8") as f:
        json.dump(signals, f, ensure_ascii=False, indent=2)
    with open(OUT_DIR / f"{out_tag}_backtest30.json", "w", encoding="utf-8") as f:
        json.dump(bt, f, ensure_ascii=False, indent=2)

    # 交易统计
    entries = [s for s in signals if s["entry_signal"]]
    exits = [s for s in signals if s["exit_signal"]]
    adds = [s for s in signals if s["add_signal"]]
    longs = [s for s in entries if "做多" in str(s.get("signal_type",""))]
    shorts = [s for s in entries if "做空" in str(s.get("signal_type",""))]

    win_trades = [t for t in trades if t["pnl_pct"] > 0]
    loss_trades = [t for t in trades if t["pnl_pct"] <= 0]
    wr = len(win_trades)/len(trades)*100 if trades else 0

    avg_w = sum(t["pnl_pct"] for t in win_trades)/len(win_trades) if win_trades else 0
    avg_l = sum(t["pnl_pct"] for t in loss_trades)/len(loss_trades) if loss_trades else 0
    pf = abs(avg_w/avg_l) if avg_l != 0 else 0

    stats = {
        "company": name, "code": code, "market": market, "currency": ccy,
        "entry_signals": len(longs), "short_signals": len(shorts),
        "exit_signals": len(exits), "add_signals": len(adds),
        "total_return_pct": bt["total_return"],
        "max_drawdown_pct": bt["max_dd"],
        "total_trades": bt["trade_count"],
        "win_rate_pct": round(wr,1),
        "profit_factor": round(pf,2),
        "final_capital": bt["final_capital"],
    }
    all_results.append(stats)

with open(OUT_DIR / "_summary30.json", "w", encoding="utf-8") as f:
    json.dump({"period": PERIOD, "exit_period": EXIT_PERIOD, "stocks": all_results}, f, ensure_ascii=False, indent=2)

# ============================================================
# 打印报告
# ============================================================
print(f"\n{'='*90}")
print(f"  海龟策略回测报告 — 通道周期 = {PERIOD} 日")
print(f"{'='*90}")
print(f"  入场: 突破{PERIOD}日通道  |  出场: 突破{EXIT_PERIOD}日通道 |  2ATR止损 | 每0.5ATR加仓")
print()
print(f"{'标的':14s} {'做多':>4s} {'做空':>4s} {'交易':>4s} {'收益率':>8s} {'最大回撤':>8s} {'胜率':>6s} {'盈亏比':>7s}")
print(f"{'-'*70}")

for s in all_results:
    print(f"{s['company']:6s}({s['code']:6s}) {s['entry_signals']:>4d} {s['short_signals']:>4d} {s['total_trades']:>4d} {s['total_return_pct']:>+7.2f}% {s['max_drawdown_pct']:>7.2f}% {s['win_rate_pct']:>5.1f}% {s['profit_factor']:>7.2f}")

print(f"{'-'*70}")
avg_r = sum(s['total_return_pct'] for s in all_results)/len(all_results)
avg_dd = sum(s['max_drawdown_pct'] for s in all_results)/len(all_results)
avg_wr = sum(s['win_rate_pct'] for s in all_results)/len(all_results)
avg_pf = sum(s['profit_factor'] for s in all_results)/len(all_results)
print(f"{'8只平均':14s} {'':4s} {'':4s} {'':4s} {avg_r:>+7.2f}% {avg_dd:>7.2f}% {avg_wr:>5.1f}% {avg_pf:>7.2f}")

# 对比20日
print(f"\n{'='*90}")
print(f"  对比分析: 30日通道 vs 20日通道")
print(f"{'='*90}")

# 加载20日结果
with open("data/backtest/_backtest_summary.json", "r", encoding="utf-8") as f:
    bt20 = json.load(f)

print(f"\n{'指标':>12s} {'20日通道':>10s} {'30日通道':>10s} {'变化':>10s}")
print(f"{'-'*42}")
r20_avg = sum(r['metrics']['total_return_pct'] for r in bt20['results'])/8
dd20_avg = sum(r['metrics']['max_drawdown_pct'] for r in bt20['results'])/8
wr20_avg = sum(r['metrics']['win_rate_pct'] for r in bt20['results'])/8
pf20_avg = sum(r['metrics']['profit_factor'] for r in bt20['results'] if r['metrics']['profit_factor']<100)/8
tc20 = sum(r['metrics']['total_trades'] for r in bt20['results'])
tc30 = sum(s['total_trades'] for s in all_results)
sig20 = sum(r['metrics']['win_trades']+r['metrics']['loss_trades'] for r in bt20['results'])

print(f"{'平均收益率':>12s} {r20_avg:>+9.2f}% {avg_r:>+9.2f}% {(avg_r-r20_avg):>+9.2f}%")
print(f"{'最大回撤':>12s} {dd20_avg:>9.2f}% {avg_dd:>9.2f}% {(avg_dd-dd20_avg):>+9.2f}%")
print(f"{'胜率':>12s} {wr20_avg:>8.1f}% {avg_wr:>8.1f}% {(avg_wr-wr20_avg):>+8.1f}%")
print(f"{'盈亏比':>12s} {pf20_avg:>9.2f} {avg_pf:>9.2f} {(avg_pf-pf20_avg):>+9.2f}")
print(f"{'总交易数':>12s} {tc20:>9d} {tc30:>9d} {(tc30-tc20):>+9d}")

print(f"\n{'='*90}")
print(f"  完整数据已保存至: {OUT_DIR}")
