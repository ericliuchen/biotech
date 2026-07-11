#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基于 MA(5)/MA(15) 金叉/死叉生成买入卖出交易信号，并模拟完整交易回测。

策略规则:
  - 金叉 (MA5 上穿 MA15) → 产生 BUY 信号
  - 死叉 (MA5 下穿 MA15) → 产生 SELL 信号
  - 信号产生当日收盘确认，次日开盘价执行交易
  - 单标的单次持仓，不加仓不做空
  - 期末若仍持仓，按最后收盘价计算未实现盈亏

输出:
  data/signals/{stock}_signals.json   — 每日信号明细 (全量)
  data/signals/{stock}_trades.json    — 交易记录
  data/signals/signal_summary.json    — 全标的绩效汇总
"""
import json
import os

BASE_DIR = r"D:\AI\线上学习"
IND_DIR  = os.path.join(BASE_DIR, "data", "indicators")
SIG_DIR  = os.path.join(BASE_DIR, "data", "signals")

# 读取汇总
with open(os.path.join(IND_DIR, "ma_summary.json"), "r", encoding="utf-8") as f:
    summary_data = json.load(f)

STOCKS = summary_data["stocks"]
SHORT_MA = summary_data["meta"]["short_ma"]   # 5
LONG_MA  = summary_data["meta"]["long_ma"]     # 15
MA5_KEY = f"ma{SHORT_MA}"
MA15_KEY = f"ma{LONG_MA}"


def run_backtest(records, stock_info):
    """
    对单标的运行 MA 交叉策略回测。
    返回: (daily_signals, trade_records, performance)
    """
    n = len(records)
    daily = []       # 每日信号明细
    trades = []      # 交易记录
    position = None  # None=空仓; dict=持仓信息

    for i in range(n):
        rec = records[i]
        ma_sig = rec.get("ma_signal", "")  # "金叉" / "死叉" / ""

        # ── 确定当日交易意图 ──
        intent = "HOLD"
        if ma_sig == "金叉" and position is None:
            intent = "BUY"
        elif ma_sig == "死叉" and position is not None:
            intent = "SELL"

        # ── 执行交易 (次日开盘价) ──
        exec_note = ""
        exec_price = None

        if intent == "BUY" and i + 1 < n:
            next_rec = records[i + 1]
            entry_price = next_rec["open"]
            entry_date = next_rec["trade_date"]
            position = {
                "entry_date": entry_date,
                "entry_price": entry_price,
                "entry_idx": i + 1,
            }
            exec_note = f"→ 次日({entry_date})开盘买入 @ {entry_price}"
            exec_price = entry_price

        elif intent == "SELL" and i + 1 < n:
            next_rec = records[i + 1]
            exit_price = next_rec["open"]
            exit_date = next_rec["trade_date"]
            holding_days = (i + 1) - position["entry_idx"]
            pnl = round(exit_price - position["entry_price"], 4)
            pnl_pct = round((exit_price / position["entry_price"] - 1) * 100, 2)

            trade = {
                "trade_id": len(trades) + 1,
                "entry_date": position["entry_date"],
                "entry_price": position["entry_price"],
                "exit_date": exit_date,
                "exit_price": exit_price,
                "holding_days": holding_days,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "result": "盈利" if pnl > 0 else ("亏损" if pnl < 0 else "持平"),
            }
            trades.append(trade)
            exec_note = f"→ 次日({exit_date})开盘卖出 @ {exit_price} (盈亏: {pnl_pct}%)"
            exec_price = exit_price
            position = None

        # ── 构建当日记录 ──
        daily.append({
            "trade_date": rec["trade_date"],
            "open": rec["open"],
            "high": rec["high"],
            "low": rec["low"],
            "close": rec["close"],
            "volume": rec["volume"],
            MA5_KEY: rec.get(MA5_KEY),
            MA15_KEY: rec.get(MA15_KEY),
            "ma_signal": ma_sig,
            "trade_signal": intent,
            "position": "持仓" if position else "空仓",
            "exec_note": exec_note,
        })

    # ── 期末未平仓处理 ──
    unrealized_pnl = None
    unrealized_pnl_pct = None
    if position is not None:
        last_rec = records[-1]
        exit_price = last_rec["close"]
        exit_date = last_rec["trade_date"]
        unrealized_pnl = round(exit_price - position["entry_price"], 4)
        unrealized_pnl_pct = round((exit_price / position["entry_price"] - 1) * 100, 2)

        trades.append({
            "trade_id": len(trades) + 1,
            "entry_date": position["entry_date"],
            "entry_price": position["entry_price"],
            "exit_date": exit_date,
            "exit_price": exit_price,
            "holding_days": n - 1 - position["entry_idx"],
            "pnl": unrealized_pnl,
            "pnl_pct": unrealized_pnl_pct,
            "result": "未平仓",
        })

    # ── 绩效统计 ──
    closed = [t for t in trades if t["result"] != "未平仓"]
    wins = [t for t in closed if t["pnl"] > 0]
    losses = [t for t in closed if t["pnl"] < 0]

    total_pnl = round(sum(t["pnl"] for t in trades), 4)
    win_rate = round(len(wins) / len(closed) * 100, 1) if closed else 0
    avg_hold = round(sum(t["holding_days"] for t in closed) / len(closed), 1) if closed else 0
    max_win = max(closed, key=lambda x: x["pnl_pct"]) if closed else None
    max_loss = min(closed, key=lambda x: x["pnl_pct"]) if closed else None

    # 买卖信号统计
    buy_signals = sum(1 for d in daily if d["trade_signal"] == "BUY")
    sell_signals = sum(1 for d in daily if d["trade_signal"] == "SELL")

    perf = {
        "name": stock_info["name"],
        "market": stock_info["market"],
        "code": stock_info["code"],
        "currency": stock_info["currency"],
        "buy_signals": buy_signals,
        "sell_signals": sell_signals,
        "total_trades": len(trades),
        "closed_trades": len(closed),
        "win_trades": len(wins),
        "loss_trades": len(losses),
        "win_rate_pct": win_rate,
        "total_pnl": total_pnl,
        "avg_holding_days": avg_hold,
        "max_win_trade_pct": max_win["pnl_pct"] if max_win else None,
        "max_win_trade": f"{max_win['entry_date']}→{max_win['exit_date']}" if max_win else None,
        "max_loss_trade_pct": max_loss["pnl_pct"] if max_loss else None,
        "max_loss_trade": f"{max_loss['entry_date']}→{max_loss['exit_date']}" if max_loss else None,
        "current_position": "持仓中" if position else "空仓",
        "unrealized_pnl": unrealized_pnl,
        "unrealized_pnl_pct": unrealized_pnl_pct,
        "latest_close": records[-1]["close"],
        "latest_ma5": records[-1].get(MA5_KEY),
        "latest_ma15": records[-1].get(MA15_KEY),
    }

    return daily, trades, perf


def main():
    os.makedirs(SIG_DIR, exist_ok=True)
    all_perf = []

    for stock in STOCKS:
        label = f"{stock['name']}({stock['market']})"
        ind_path = os.path.join(IND_DIR, stock["file_indicators"])

        print(f"\n{'='*60}")
        print(f"处理: {label}  代码: {stock['code']}")
        print(f"{'='*60}")

        with open(ind_path, "r", encoding="utf-8") as f:
            records = json.load(f)

        print(f"  数据: {len(records)} 条 ({records[0]['trade_date']} ~ {records[-1]['trade_date']})")

        daily, trades, perf = run_backtest(records, stock)

        # 保存每日信号
        sig_name = stock["file_indicators"].replace("_ma.json", "_signals.json")
        sig_path = os.path.join(SIG_DIR, sig_name)
        with open(sig_path, "w", encoding="utf-8") as f:
            json.dump(daily, f, ensure_ascii=False, indent=2)

        # 保存交易记录
        trd_name = stock["file_indicators"].replace("_ma.json", "_trades.json")
        trd_path = os.path.join(SIG_DIR, trd_name)
        with open(trd_path, "w", encoding="utf-8") as f:
            json.dump(trades, f, ensure_ascii=False, indent=2)

        all_perf.append(perf)

        # ── 控制台输出 ──
        print(f"  买入信号: {perf['buy_signals']}  卖出信号: {perf['sell_signals']}")
        print(f"  总交易: {perf['total_trades']}  已平仓: {perf['closed_trades']}")
        print(f"  胜率: {perf['win_rate_pct']}%  (盈{perf['win_trades']}/亏{perf['loss_trades']})")
        print(f"  总盈亏: {perf['total_pnl']} {stock['currency']}")
        print(f"  平均持仓: {perf['avg_holding_days']} 天")
        if perf["max_win_trade_pct"] is not None:
            print(f"  最佳交易: +{perf['max_win_trade_pct']}%  ({perf['max_win_trade']})")
        if perf["max_loss_trade_pct"] is not None:
            print(f"  最差交易: {perf['max_loss_trade_pct']}%  ({perf['max_loss_trade']})")
        print(f"  当前: {perf['current_position']}" +
              (f"  未实现: {perf['unrealized_pnl_pct']}%" if perf["unrealized_pnl_pct"] is not None else ""))

        print(f"\n  {'ID':>3} {'买入日':<12} {'买入价':>10} {'卖出日':<16} {'卖出价':>10} {'天数':>5} {'盈亏%':>8} {'结果'}")
        print(f"  {'─'*78}")
        for t in trades:
            print(f"  {t['trade_id']:>3} {t['entry_date']:<12} {t['entry_price']:>10.2f} {t['exit_date']:<16} {t['exit_price']:>10.2f} {t['holding_days']:>5} {t['pnl_pct']:>8.2f} {t['result']}")

    # ─── 汇总 ───
    summary_path = os.path.join(SIG_DIR, "signal_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "meta": {
                "description": "8个标的 MA(5)/MA(15) 交叉策略交易信号回测汇总",
                "strategy": "MA金叉买入, MA死叉卖出, 信号次日开盘价执行, 单仓不做空",
                "short_ma": SHORT_MA,
                "long_ma": LONG_MA,
                "start_date": summary_data["meta"]["start_date"],
                "end_date": summary_data["meta"]["end_date"],
                "data_source": summary_data["meta"]["data_source"],
                "generated": "2026-07-11",
            },
            "stocks": all_perf,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"汇总报告 → {summary_path}")
    print(f"{'='*60}")

    # 汇总表
    print(f"\n{'标的':<10} {'市场':<5} {'买入':>4} {'卖出':>4} {'交易':>4} {'胜率':>7} {'总盈亏':>12} {'均仓天':>6} {'当前':>6}")
    print("─" * 80)
    for p in all_perf:
        print(f"{p['name']:<10} {p['market']:<5} {p['buy_signals']:>4} {p['sell_signals']:>4} "
              f"{p['total_trades']:>4} {p['win_rate_pct']:>6.1f}% "
              f"{p['total_pnl']:>10.2f} {p['currency']:<3} {p['avg_holding_days']:>5.1f} "
              f"{p['current_position']:>6}")


if __name__ == "__main__":
    main()
