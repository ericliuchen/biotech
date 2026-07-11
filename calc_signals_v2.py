import json
import sys
import io
from pathlib import Path

# Fix terminal encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

STD_DIR = Path("D:/AI/线上学习/data/standardized")
OUT_DIR = Path("D:/AI/线上学习/data/signals")
OUT_DIR.mkdir(parents=True, exist_ok=True)

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

def calc_atr_wilder(data, period):
    """计算 ATR (Wilder 平滑)"""
    tr_list = []
    atr_list = []
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

def generate_turtle_signals(data):
    """
    海龟策略完整交易信号
    
    入场: 今日收盘价 > 前20日最高价 (做多) / < 前20日最低价 (做空)
    加仓: 每 0.5 ATR 加一次，最多4次
    出场: 价格跌破10日低点 (做多) / 突破10日高点 (做空)
    硬止损: 2 ATR 无条件止损
    浮盈保护: 盈利超10ATR后止损移至入场价
    """
    n = len(data)
    atr_list = calc_atr_wilder(data, 20)

    signals = []
    position = False
    position_type = None  # "long" or "short"
    entry_price = 0
    entry_date = ""
    add_count = 0
    stop_loss_price = 0
    highest_since_entry = 0
    lowest_since_entry = float('inf')
    total_trades = []
    pause_until = ""  # 出场后冷却期

    for i in range(n):
        d = data[i]
        date = d["trade_date"]
        close = d["close"]
        high = d["high"]
        low = d["low"]
        atr = atr_list[i]

        # === 通道计算（仅用历史数据）===
        if i >= 20:
            prev20_high = max(data[j]["high"] for j in range(i-20, i))
            prev20_low  = min(data[j]["low"] for j in range(i-20, i))
        else:
            prev20_high = None
            prev20_low = None

        if i >= 10:
            prev10_high = max(data[j]["high"] for j in range(i-10, i))
            prev10_low  = min(data[j]["low"] for j in range(i-10, i))
        else:
            prev10_high = None
            prev10_low = None

        signal = {
            "trade_date": date,
            "close": close,
            "high": high,
            "low": low,
            "volume": d.get("volume", 0),
            "currency": d.get("currency", ""),
            "atr": round(atr, 4),
            "prev20_high": round(prev20_high, 2) if prev20_high else None,
            "prev20_low": round(prev20_low, 2) if prev20_low else None,
            "prev10_high": round(prev10_high, 2) if prev10_high else None,
            "prev10_low": round(prev10_low, 2) if prev10_low else None,
            "entry_signal": False,
            "exit_signal": False,
            "add_signal": False,
            "signal_type": None,
            "signal_price": None,
            "stop_loss": None,
            "position": position,
        }

        # === 持仓管理 ===
        if position:
            # 更新极值
            if position_type == "long":
                highest_since_entry = max(highest_since_entry, high)
            else:
                lowest_since_entry = min(lowest_since_entry, low)

            stopped_out = False

            # 第1层：2 ATR 硬止损
            if position_type == "long" and low <= stop_loss_price:
                signal["exit_signal"] = True
                signal["signal_type"] = "止损出场 (2ATR)"
                signal["signal_price"] = round(close, 2)
                stopped_out = True
                exit_reason = "止损 (2ATR)"
            elif position_type == "short" and high >= stop_loss_price:
                signal["exit_signal"] = True
                signal["signal_type"] = "止损出场 (2ATR)"
                signal["signal_price"] = round(close, 2)
                stopped_out = True
                exit_reason = "止损 (2ATR)"

            # 第2层：反向突破 10 日通道
            elif position_type == "long" and low <= prev10_low:
                signal["exit_signal"] = True
                signal["signal_type"] = "出场 (跌破10日低点)"
                signal["signal_price"] = round(prev10_low, 2)
                stopped_out = True
                exit_reason = "趋势反转 (10日通道)"
            elif position_type == "short" and high >= prev10_high:
                signal["exit_signal"] = True
                signal["signal_type"] = "出场 (突破10日高点)"
                signal["signal_price"] = round(prev10_high, 2)
                stopped_out = True
                exit_reason = "趋势反转 (10日通道)"

            if stopped_out:
                total_trades.append({
                    "entry_date": entry_date,
                    "entry_price": round(entry_price, 2),
                    "position_type": position_type,
                    "exit_date": date,
                    "exit_price": round(close, 2),
                    "pnl_pct": round((close - entry_price) / entry_price * 100 * (1 if position_type == "long" else -1), 2),
                    "reason": exit_reason,
                    "add_count": add_count,
                    "highest_reached": round(highest_since_entry, 2) if position_type == "long" else round(lowest_since_entry, 2),
                })
                position = False
                position_type = None
                entry_price = 0
                entry_date = ""
                add_count = 0
                stop_loss_price = 0
                highest_since_entry = 0
                lowest_since_entry = float('inf')
                pause_until = date  # 当天不再入场

            else:
                # 第3层：浮盈回撤管理
                if position_type == "long":
                    if highest_since_entry >= entry_price + 10 * atr:
                        # 止损线移至保本
                        if stop_loss_price < entry_price:
                            stop_loss_price = entry_price
                            signal["signal_type"] = "止损上移至保本"
                else:
                    if lowest_since_entry <= entry_price - 10 * atr:
                        if stop_loss_price > entry_price:
                            stop_loss_price = entry_price
                            signal["signal_type"] = "止损下移至保本"

                # 加仓检查（有浮盈时）
                if position_type == "long" and add_count < 4:
                    add_step = 0.5 * atr
                    next_add = entry_price + (add_count + 1) * add_step
                    if close >= next_add:
                        signal["add_signal"] = True
                        add_count += 1
                        signal["signal_type"] = f"加仓 第{add_count}次 (+{add_count*0.5:.1f}ATR)"
                        signal["signal_price"] = round(next_add, 2)

        # === 入场信号（空仓时）===
        if not position and prev20_high is not None and prev20_low is not None:
            # 做多：收盘价 > 前20日最高点
            if close > prev20_high:
                signal["entry_signal"] = True
                signal["signal_type"] = "做多入场 (突破20日高点)"
                signal["signal_price"] = round(close, 2)
                position = True
                position_type = "long"
                entry_price = close
                entry_date = date
                add_count = 0
                stop_loss_price = entry_price - 2 * atr
                highest_since_entry = high
                lowest_since_entry = float('inf')

            # 做空：收盘价 < 前20日最低点
            elif close < prev20_low:
                signal["entry_signal"] = True
                signal["signal_type"] = "做空入场 (跌破20日低点)"
                signal["signal_price"] = round(close, 2)
                position = True
                position_type = "short"
                entry_price = close
                entry_date = date
                add_count = 0
                stop_loss_price = entry_price + 2 * atr
                highest_since_entry = 0
                lowest_since_entry = low

        # 更新止损位
        if position:
            signal["stop_loss"] = round(stop_loss_price, 2)

        signal["position"] = position
        signals.append(signal)

    return signals, total_trades


all_reports = []

for fname, (company, code, market, currency) in STOCK_MAP.items():
    filepath = STD_DIR / fname
    with open(filepath, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    raw_data.sort(key=lambda x: x["trade_date"])

    signals, trades = generate_turtle_signals(raw_data)

    out_name = fname.replace("_std.json", "_signals_v2.json")
    out_path = OUT_DIR / out_name
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(signals, f, ensure_ascii=False, indent=2)

    trades_name = fname.replace("_std.json", "_trades_v2.json")
    trades_path = OUT_DIR / trades_name
    with open(trades_path, "w", encoding="utf-8") as f:
        json.dump(trades, f, ensure_ascii=False, indent=2)

    # === 统计 ===
    entries = [s for s in signals if s["entry_signal"]]
    exits = [s for s in signals if s["exit_signal"]]
    adds = [s for s in signals if s["add_signal"]]
    longs = [s for s in entries if s["signal_type"] and "做多" in s["signal_type"]]
    shorts = [s for s in entries if s["signal_type"] and "做空" in s["signal_type"]]
    latest = signals[-1]

    # 最近信号
    last_sigs = [s for s in signals[-90:] if s["entry_signal"] or s["exit_signal"] or s["add_signal"]]
    recent = last_sigs[-1] if last_sigs else {}

    # 交易统计
    win = [t for t in trades if t["pnl_pct"] > 0]
    loss = [t for t in trades if t["pnl_pct"] <= 0]
    win_rate = len(win) / len(trades) * 100 if trades else 0

    # 判断当前持仓方向
    pos_type = None
    if latest["position"]:
        for s in reversed(signals[-30:]):
            if s["position"] and s.get("signal_type") and "做多" in str(s["signal_type"]):
                pos_type = "long"
                break
            elif s["position"] and s.get("signal_type") and "做空" in str(s["signal_type"]):
                pos_type = "short"
                break

    report = {
        "company": company, "code": code, "market": market, "currency": currency,
        "total_days": len(signals),
        "long_signals": len(longs), "short_signals": len(shorts),
        "add_signals": len(adds), "completed_trades": len(trades),
        "win_trades": len(win), "loss_trades": len(loss),
        "win_rate_pct": round(win_rate, 1),
        "is_in_position": latest["position"],
        "position_type": pos_type,
    }

    if trades:
        avg_win = sum(t["pnl_pct"] for t in win) / len(win) if win else 0
        avg_loss = sum(t["pnl_pct"] for t in loss) / len(loss) if loss else 0
        report["avg_win_pct"] = round(avg_win, 2)
        report["avg_loss_pct"] = round(avg_loss, 2)
        report["profit_factor"] = round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else None
        best = max(trades, key=lambda t: t["pnl_pct"])
        worst = min(trades, key=lambda t: t["pnl_pct"])
        report["best_trade_pct"] = best["pnl_pct"]
        report["best_trade"] = f"{best['entry_date']}~{best['exit_date']} ({best['position_type']})"
        report["worst_trade_pct"] = worst["pnl_pct"]
        report["worst_trade"] = f"{worst['entry_date']}~{worst['exit_date']} ({worst['position_type']})"

    all_reports.append(report)

    # 打印报告
    pos_mark = "[持仓中]" if latest["position"] else "[空仓]"
    print(f"\n{'='*60}")
    print(f"  {company} ({code} {market})")
    print(f"{'='*60}")
    print(f"  数据区间: {signals[0]['trade_date']} ~ {signals[-1]['trade_date']}  ({len(signals)}天)")
    print(f"  做多信号: {len(longs):3d}次  |  做空信号: {len(shorts):3d}次  |  加仓信号: {len(adds):3d}次")
    print(f"  完成交易: {len(trades):3d}笔  |  胜率: {report['win_rate_pct']:5.1f}%")
    if trades:
        print(f"  平均盈利: {avg_win:+.2f}%  |  平均亏损: {avg_loss:+.2f}%  |  盈亏比: {report['profit_factor']}")
        print(f"  最佳: {best['pnl_pct']:+.2f}% [{best['entry_date']}~{best['exit_date']}]")
        print(f"  最差: {worst['pnl_pct']:+.2f}% [{worst['entry_date']}~{worst['exit_date']}]")
    print(f"  当前状态: {pos_mark}")

# 保存汇总
summary_file = OUT_DIR / "_trading_summary_v2.json"
with open(summary_file, "w", encoding="utf-8") as f:
    json.dump({
        "method": "海龟策略 (Turtle Trading)",
        "rules": {
            "entry_long": "收盘价 > 前20日最高点",
            "entry_short": "收盘价 < 前20日最低点",
            "exit_long": "跌破10日低点 或 2ATR止损 或 浮盈管理",
            "exit_short": "突破10日高点 或 2ATR止损 或 浮盈管理",
            "add": "每0.5ATR加仓一次，最多4次",
        },
        "stocks": all_reports,
        "generated": "2026-07-11"
    }, f, ensure_ascii=False, indent=2)

print(f"\n{'='*60}")
print(f"  ✅ 全部交易信号已生成!")
print(f"  数据目录: {OUT_DIR}")
