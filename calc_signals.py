import json
from pathlib import Path

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

def calc_donchian(data, period):
    """计算唐奇安通道"""
    result = []
    for i in range(len(data)):
        if i < period - 1:
            result.append({"upper": None, "lower": None, "middle": None})
        else:
            window = data[i - period + 1 : i + 1]
            upper = max(d["high"] for d in window)
            lower = min(d["low"] for d in window)
            result.append({"upper": upper, "lower": lower, "middle": (upper + lower) / 2})
    return result

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

def has_position(signals, idx):
    """检查在给定索引处是否持有仓位"""
    position = False
    entry_price = 0
    entry_date = ""
    add_count = 0
    for i in range(idx, -1, -1):
        sig = signals[i]
        if sig.get("exit_signal"):
            position = False
            entry_price = 0
            entry_date = ""
            add_count = 0
        elif sig.get("entry_signal"):
            position = True
            entry_price = sig.get("signal_price", 0) or sig.get("close", 0)
            entry_date = sig["trade_date"]
            add_count = 0
        elif sig.get("add_signal"):
            add_count += 1
    return position, entry_price, entry_date, add_count

def generate_turtle_signals(data):
    """生成完整海龟交易信号"""
    n = len(data)
    ch20 = calc_donchian(data, 20)
    ch10 = calc_donchian(data, 10)
    atr_list = calc_atr_wilder(data, 20)

    signals = []
    position = False       # 当前是否持仓
    entry_price = 0        # 入场价
    entry_date = ""         # 入场日期
    add_count = 0            # 加仓次数
    stop_loss_price = 0     # 当前止损价
    highest_since_entry = 0 # 入场后最高价（用于移动止损）
    total_trades = []

    for i in range(n):
        d = data[i]
        date = d["trade_date"]
        close = d["close"]
        high = d["high"]
        low = d["low"]
        atr = atr_list[i]
        ch20_u = ch20[i]["upper"]
        ch20_l = ch20[i]["lower"]
        ch10_l = ch10[i]["lower"]
        ch10_u = ch10[i]["upper"]

        signal_info = {
            "trade_date": date,
            "close": close,
            "high": high,
            "low": low,
            "volume": d.get("volume", 0),
            "currency": d.get("currency", ""),
            "atr": round(atr, 4) if atr else None,
            "channel20_upper": round(ch20_u, 2) if ch20_u else None,
            "channel20_lower": round(ch20_l, 2) if ch20_l else None,
            "channel10_lower": round(ch10_l, 2) if ch10_l else None,
            "channel10_upper": round(ch10_u, 2) if ch10_u else None,
            "entry_signal": False,
            "exit_signal": False,
            "add_signal": False,
            "signal_type": None,
            "signal_price": None,
            "stop_loss": None,
            "position": False,
        }

        # 更新持仓后最高价（移动止损用）
        if position:
            highest_since_entry = max(highest_since_entry, high)
            # 三层止损检查
            # 第1层：2 ATR 硬止损
            if low <= stop_loss_price:
                signal_info["exit_signal"] = True
                signal_info["signal_type"] = "止损出场 (2 ATR)"
                signal_info["stop_loss"] = round(stop_loss_price, 2)
                # 记录交易
                total_trades.append({
                    "entry_date": entry_date,
                    "entry_price": round(entry_price, 2),
                    "exit_date": date,
                    "exit_price": round(close, 2),
                    "pnl_pct": round((close - entry_price) / entry_price * 100, 2),
                    "reason": "止损 (2 ATR)",
                    "add_count": add_count
                })
                position = False
                entry_price = 0
                entry_date = ""
                add_count = 0
                stop_loss_price = 0
                highest_since_entry = 0

            # 第2层：反向突破 10 日通道
            elif low <= ch10_l:
                signal_info["exit_signal"] = True
                signal_info["signal_type"] = "出场 (跌破10日低点)"
                signal_info["stop_loss"] = round(ch10_l, 2)
                total_trades.append({
                    "entry_date": entry_date,
                    "entry_price": round(entry_price, 2),
                    "exit_date": date,
                    "exit_price": round(close, 2),
                    "pnl_pct": round((close - entry_price) / entry_price * 100, 2),
                    "reason": "趋势反转 (10日通道)",
                    "add_count": add_count
                })
                position = False
                entry_price = 0
                entry_date = ""
                add_count = 0
                stop_loss_price = 0
                highest_since_entry = 0

            else:
                # 第3层：浮盈回撤管理
                if position and highest_since_entry >= entry_price + 10 * atr:
                    # 移动止损至入场价（保本）
                    pass  # 止损价已在入场时设置

        # 入场信号（仅在未持仓时）
        if not position and ch20_u is not None and ch20_l is not None:
            # 做多：价格突破20日高点
            if close > ch20_u:
                signal_info["entry_signal"] = True
                signal_info["signal_type"] = "做多入场 (突破20日高点)"
                signal_info["signal_price"] = round(ch20_u, 2)
                position = True
                entry_price = ch20_u
                entry_date = date
                add_count = 0
                stop_loss_price = entry_price - 2 * atr
                highest_since_entry = max(high, ch20_u)

            # 做空：价格跌破20日低点
            elif close < ch20_l:
                signal_info["entry_signal"] = True
                signal_info["signal_type"] = "做空入场 (跌破20日低点)"
                signal_info["signal_price"] = round(ch20_l, 2)
                position = True
                entry_price = ch20_l
                entry_date = date
                add_count = 0
                stop_loss_price = entry_price + 2 * atr
                highest_since_entry = max(high, ch20_l)

        # 加仓信号（持仓中）
        elif position and add_count < 4:
            add_step = 0.5 * atr
            next_add_price = entry_price + (add_count + 1) * add_step
            if close >= next_add_price:
                signal_info["add_signal"] = True
                signal_info["signal_type"] = f"加仓 (第{add_count+1}次)"
                signal_info["signal_price"] = round(next_add_price, 2)
                add_count += 1

        signal_info["position"] = position

        # 更新当前止损价
        if position:
            # 浮盈超过10 ATR后，将止损线上移至入场价（保本）
            if highest_since_entry >= entry_price + 10 * atr:
                signal_info["stop_loss"] = round(entry_price, 2)
            else:
                signal_info["stop_loss"] = round(stop_loss_price, 2)

        signals.append(signal_info)

    return signals, total_trades


all_reports = []

for fname, (company, code, market, currency) in STOCK_MAP.items():
    filepath = STD_DIR / fname
    with open(filepath, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    raw_data.sort(key=lambda x: x["trade_date"])

    signals, trades = generate_turtle_signals(raw_data)

    # 保存信号数据
    out_name = fname.replace("_std.json", "_signals.json")
    out_path = OUT_DIR / out_name
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(signals, f, ensure_ascii=False, indent=2)

    # 保存完整交易记录
    trades_name = fname.replace("_std.json", "_trades.json")
    trades_path = OUT_DIR / trades_name
    with open(trades_path, "w", encoding="utf-8") as f:
        json.dump(trades, f, ensure_ascii=False, indent=2)

    # === 统计信息 ===
    entries = [s for s in signals if s["entry_signal"]]
    exits = [s for s in signals if s["exit_signal"]]
    adds = [s for s in signals if s["add_signal"]]
    latest = signals[-1]

    # 最近一次信号
    last_signals = [s for s in signals[-60:] if s["entry_signal"] or s["exit_signal"] or s["add_signal"]]
    recent = last_signals[-1] if last_signals else {}
    recent_signal_type = recent.get("signal_type", "无")
    recent_date = recent.get("trade_date", "") if recent else ""

    # 交易统计
    win_trades = [t for t in trades if t["pnl_pct"] > 0]
    loss_trades = [t for t in trades if t["pnl_pct"] <= 0]
    win_rate = len(win_trades) / len(trades) * 100 if trades else 0

    report = {
        "company": company,
        "code": code,
        "market": market,
        "currency": currency,
        "total_days": len(signals),
        "entry_signals": len(entries),
        "exit_signals": len(exits),
        "add_signals": len(adds),
        "completed_trades": len(trades),
        "win_trades": len(win_trades),
        "loss_trades": len(loss_trades),
        "win_rate_pct": round(win_rate, 1),
        "is_in_position": latest["position"],
        "latest_signal_type": recent_signal_type,
        "latest_signal_date": recent_date,
        "current_stop_loss": latest.get("stop_loss"),
    }

    if trades:
        avg_win = sum(t["pnl_pct"] for t in win_trades) / len(win_trades) if win_trades else 0
        avg_loss = sum(t["pnl_pct"] for t in loss_trades) / len(loss_trades) if loss_trades else 0
        report["avg_win_pct"] = round(avg_win, 2)
        report["avg_loss_pct"] = round(avg_loss, 2)
        report["profit_factor"] = round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else float('inf')
        best_trade = max(trades, key=lambda t: t["pnl_pct"])
        worst_trade = min(trades, key=lambda t: t["pnl_pct"])
        report["best_trade_pct"] = best_trade["pnl_pct"]
        report["best_trade_dates"] = f"{best_trade['entry_date']} → {best_trade['exit_date']}"
        report["worst_trade_pct"] = worst_trade["pnl_pct"]
        report["worst_trade_dates"] = f"{worst_trade['entry_date']} → {worst_trade['exit_date']}"

    all_reports.append(report)

    # 打印摘要
    pos_mark = "📌 持仓中" if latest["position"] else "空仓"
    print(f"\n{'='*60}")
    print(f"  {company} ({code} {market})")
    print(f"{'='*60}")
    print(f"  数据区间: {signals[0]['trade_date']} ~ {signals[-1]['trade_date']} ({len(signals)}个交易日)")
    print(f"  买入信号: {len(entries)} 次  |  卖出信号: {len(exits)} 次  |  加仓信号: {len(adds)} 次")
    print(f"  完成交易: {len(trades)} 笔  |  胜率: {report['win_rate_pct']:.1f}%  |  盈亏比: {report.get('profit_factor', 'N/A')}")
    print(f"  当前状态: {pos_mark}  |  止损位: {latest.get('stop_loss', 'N/A')}")
    print(f"  最近信号: [{recent_date}] {recent_signal_type}")
    if trades:
        print(f"  最佳交易: {report['best_trade_pct']:+.2f}% ({report['best_trade_dates']})")
        print(f"  最差交易: {report['worst_trade_pct']:+.2f}% ({report['worst_trade_dates']})")

# 保存汇总
summary_file = OUT_DIR / "_trading_summary.json"
with open(summary_file, "w", encoding="utf-8") as f:
    json.dump({
        "period": "2025-07 ~ 2026-07",
        "method": "海龟策略 (Turtle Trading)",
        "rules": {
            "entry": "价格突破20日高点/低点",
            "exit": "价格跌破10日低点/高点 或 2ATR止损",
            "add": "每0.5ATR加仓一次，最多4次",
            "stop_loss": "第1层: 2ATR, 第2层: 10日通道, 第3层: 浮盈10ATR后移至保本"
        },
        "stocks": all_reports
    }, f, ensure_ascii=False, indent=2)

print(f"\n{'='*60}")
print(f"  所有交易信号已生成!")
print(f"  数据目录: {OUT_DIR}")
print(f"  汇总文件: {summary_file}")
print(f"{'='*60}")
