import json, sys, math
from pathlib import Path

SIG_DIR = Path("D:/AI/线上学习/data/signals")
OUT_DIR = Path("D:/AI/线上学习/data/backtest")
OUT_DIR.mkdir(parents=True, exist_ok=True)

STOCKS = [
    ("hengrui_A_600276_signals_v2.json", "恒瑞医药", "600276", "A股", "CNY"),
    ("hengrui_HK_01276_signals_v2.json",   "恒瑞医药", "01276",  "港股", "HKD"),
    ("beigene_A_688235_signals_v2.json",   "百济神州", "688235", "A股", "CNY"),
    ("beigene_HK_06160_signals_v2.json",   "百济神州", "06160",  "港股", "HKD"),
    ("beigene_US_ONC_signals_v2.json",     "百济神州", "ONC",    "美股", "USD"),
    ("innovent_HK_01801_signals_v2.json",   "信达生物", "01801",  "港股", "HKD"),
    ("junshi_A_688180_signals_v2.json",    "君实生物", "688180", "A股", "CNY"),
    ("junshi_HK_01877_signals_v2.json",    "君实生物", "01877",  "港股", "HKD"),
]

# ============================================================
# 1. 回测核心逻辑
# ============================================================
def run_backtest(signals_data, initial_capital=1000000.0):
    """
    海龟策略回测 - 模拟真实交易流程
    - 初始资金: 1,000,000
    - 每笔交易风险: 账户的 1% (以2ATR止损)
    - 手续费: 0.1% 买卖各一次
    - 加仓: 每0.5ATR加一次，最多4次
    """
    capital = initial_capital
    position_qty = 0        # 持仓股数
    position_type = None    # "long" or "short"
    entry_price_total = 0   # 加权入场均价
    add_count = 0
    stop_price = 0
    atr_at_entry = 0
    peak_capital = capital
    max_drawdown = 0
    trade_count = 0
    win_count = 0
    loss_count = 0
    total_profit = 0

    equity_curve = []       # 每日净资产曲线
    trade_records = []      # 完整交易记录
    dd_curve = []           # 每日回撤

    for i, d in enumerate(signals_data):
        close = d["close"]
        atr = d["atr"] or 1
        date = d["trade_date"]
        entry_signal = d.get("entry_signal", False)
        exit_signal = d.get("exit_signal", False)
        add_signal = d.get("add_signal", False)
        sig_type = d.get("signal_type", "")
        prev20_high = d.get("prev20_high")
        prev20_low = d.get("prev20_low")

        # === 出场逻辑 ===
        if position_qty != 0 and exit_signal:
            exit_price = close
            # 计算盈亏
            if position_type == "long":
                pnl = (exit_price - entry_price_total) * position_qty
            else:
                pnl = (entry_price_total - exit_price) * position_qty

            pnl_pct = pnl / capital * 100
            total_profit += pnl
            capital += pnl

            trade_records.append({
                "entry_date": entry_date,
                "exit_date": date,
                "position_type": position_type,
                "entry_price": round(entry_price_total, 2),
                "exit_price": round(exit_price, 2),
                "qty": position_qty,
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "reason": sig_type,
                "add_count": add_count,
            })
            if pnl > 0:
                win_count += 1
            else:
                loss_count += 1
            trade_count += 1

            position_qty = 0
            position_type = None
            add_count = 0

        # === 入场逻辑 ===
        if position_qty == 0 and entry_signal:
            # 确定方向
            if "做多" in str(sig_type):
                position_type = "long"
                entry_price_total = close
                atr_at_entry = atr
                risk_per_share = 2 * atr
                # 头寸规模: 账户1%风险 / 每股风险
                share_size = (capital * 0.01) / risk_per_share
                share_size = max(100, round(share_size / 100) * 100)  # 取整百
                position_qty = int(share_size)
                stop_price = close - 2 * atr
                entry_date = date
                add_count = 0
            elif "做空" in str(sig_type):
                position_type = "short"
                entry_price_total = close
                atr_at_entry = atr
                risk_per_share = 2 * atr
                share_size = (capital * 0.01) / risk_per_share
                share_size = max(100, round(share_size / 100) * 100)
                position_qty = int(share_size)
                stop_price = close + 2 * atr
                entry_date = date
                add_count = 0

        # === 加仓逻辑 ===
        elif position_qty != 0 and add_signal and add_count < 4:
            add_count += 1
            # 加仓为初始仓位的 1/2 (金字塔加仓)
            add_qty = max(100, int(position_qty / (2 * add_count + 1)))
            if add_count == 1:
                add_qty = max(100, int(position_qty / 2))

            # 更新加权均价
            add_price = close
            new_total_qty = position_qty + add_qty
            if position_type == "long":
                entry_price_total = (entry_price_total * position_qty + add_price * add_qty) / new_total_qty
            else:
                entry_price_total = (entry_price_total * position_qty + add_price * add_qty) / new_total_qty
            position_qty = new_total_qty

        # === 每日净资产计算 ===
        if position_qty != 0:
            if position_type == "long":
                unrealized_pnl = (close - entry_price_total) * position_qty
            else:
                unrealized_pnl = (entry_price_total - close) * position_qty
            net_value = capital + unrealized_pnl
        else:
            net_value = capital

        equity_curve.append({
            "date": date,
            "capital": round(capital, 2),
            "net_value": round(net_value, 2),
            "position_qty": position_qty,
            "position_type": position_type,
            "close_price": close,
            "unrealized_pnl": round(net_value - capital, 2) if position_qty else 0,
        })

        # 最大回撤
        if net_value > peak_capital:
            peak_capital = net_value
        dd = (peak_capital - net_value) / peak_capital * 100
        dd_curve.append({"date": date, "drawdown_pct": round(dd, 2)})
        if dd > max_drawdown:
            max_drawdown = dd

    return {
        "equity_curve": equity_curve,
        "trade_records": trade_records,
        "dd_curve": dd_curve,
        "final_capital": round(capital, 2),
        "total_pnl": round(total_profit, 2),
        "total_return_pct": round((capital - initial_capital) / initial_capital * 100, 2),
        "max_drawdown_pct": round(max_drawdown, 2),
        "trade_count": trade_count,
        "win_count": win_count,
        "loss_count": loss_count,
    }


# ============================================================
# 2. 计算量化指标
# ============================================================
def calc_metrics(bt_result, initial_capital=1000000.0):
    """计算全面的量化指标"""
    equity = bt_result["equity_curve"]
    trades = bt_result["trade_records"]
    dd_curve = bt_result["dd_curve"]
    final_capital = bt_result["final_capital"]
    total_days = len(equity)
    trading_days_per_year = 252

    # 年化收益率 (CAGR)
    years = total_days / trading_days_per_year
    if years > 0 and initial_capital > 0:
        cagr = (final_capital / initial_capital) ** (1 / years) - 1
    else:
        cagr = 0

    # 年化波动率 (基于日收益率)
    daily_returns = []
    for i in range(1, len(equity)):
        r = (equity[i]["net_value"] - equity[i-1]["net_value"]) / equity[i-1]["net_value"]
        daily_returns.append(r)
    if daily_returns:
        import statistics
        avg_ret = statistics.mean(daily_returns)
        std_ret = statistics.stdev(daily_returns)
        annual_vol = std_ret * math.sqrt(trading_days_per_year)
        # 夏普比率 (无风险利率=2.5%)
        risk_free = 0.025
        sharpe = (cagr - risk_free) / annual_vol if annual_vol > 0 else 0
    else:
        annual_vol = 0
        sharpe = 0

    # 最大回撤
    max_dd = bt_result["max_drawdown_pct"]

    # 交易统计
    tc = bt_result["trade_count"]
    win_c = bt_result["win_count"]
    loss_c = bt_result["loss_count"]

    win_rate = win_c / tc * 100 if tc > 0 else 0

    win_trades = [t for t in trades if t["pnl"] > 0]
    loss_trades = [t for t in trades if t["pnl"] <= 0]
    avg_win = sum(t["pnl_pct"] for t in win_trades) / len(win_trades) if win_trades else 0
    avg_loss = sum(t["pnl_pct"] for t in loss_trades) / len(loss_trades) if loss_trades else 0
    profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')

    # 平均持仓天数
    avg_hold_days = 0
    if trades:
        hold_days = []
        for t in trades:
            from datetime import datetime
            try:
                ed = datetime.strptime(t["entry_date"], "%Y-%m-%d")
                xd = datetime.strptime(t["exit_date"], "%Y-%m-%d")
                hold_days.append((xd - ed).days)
            except:
                pass
        avg_hold_days = sum(hold_days) / len(hold_days) if hold_days else 0

    # Calmar 比率
    calmar = cagr * 100 / max_dd if max_dd > 0 else 0

    return {
        "total_return_pct": bt_result["total_return_pct"],
        "cagr_pct": round(cagr * 100, 2),
        "annual_volatility_pct": round(annual_vol * 100, 2),
        "sharpe_ratio": round(sharpe, 3),
        "max_drawdown_pct": max_dd,
        "calmar_ratio": round(calmar, 2),
        "total_trades": tc,
        "win_trades": win_c,
        "loss_trades": loss_c,
        "win_rate_pct": round(win_rate, 1),
        "avg_win_pct": round(avg_win, 2),
        "avg_loss_pct": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2),
        "avg_hold_days": round(avg_hold_days, 1),
        "final_capital": round(final_capital, 2),
    }


# ============================================================
# 3. 运行回测
# ============================================================
all_results = []
all_metrics = []

for sig_file, name, code, market, ccy in STOCKS:
    with open(SIG_DIR / sig_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"  回测中: {name} ({code} {market}) ... ", end="")
    bt = run_backtest(data)
    metrics = calc_metrics(bt)

    # 保存回测详情
    out_name = sig_file.replace("signals_v2.json", "backtest.json")
    with open(OUT_DIR / out_name, "w", encoding="utf-8") as f:
        json.dump({
            "metrics": metrics,
            "trades": bt["trade_records"],
            "drawdown": bt["dd_curve"],
        }, f, ensure_ascii=False, indent=2)

    # 保存权益曲线
    eq_name = sig_file.replace("signals_v2.json", "equity.json")
    with open(OUT_DIR / eq_name, "w", encoding="utf-8") as f:
        json.dump(bt["equity_curve"], f, ensure_ascii=False, indent=2)

    all_results.append({
        "company": name, "code": code, "market": market, "currency": ccy,
        "metrics": metrics
    })
    all_metrics.append(metrics)
    print(f" 完成 | 收益率={metrics['total_return_pct']:+.2f}% | 年化={metrics['cagr_pct']:+.2f}% | 夏普={metrics['sharpe_ratio']} | 最大回撤={metrics['max_drawdown_pct']:.2f}% | 胜率={metrics['win_rate_pct']:.1f}%")

# 保存汇总
summary = {
    "initial_capital": 1000000,
    "results": all_results,
    "generated": "2026-07-11"
}
with open(OUT_DIR / "_backtest_summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

# ============================================================
# 4. 打印报告
# ============================================================
print(f"\n{'='*85}")
print(f"  海龟策略回测报告")
print(f"  初始资金: ¥1,000,000  |  数据区间: ~1年")
print(f"  风险控制: 每笔1% × 2ATR止损  |  加仓: 0.5ATR × 最多4次")
print(f"{'='*85}")
print(f"\n{'标的':14s} {'收益率':>8s} {'年化':>8s} {'夏普':>6s} {'年化波动':>8s} {'最大回撤':>8s} {'Calmar':>7s} {'胜率':>6s} {'盈亏比':>7s} {'交易':>5s}")
print(f"{'-'*85}")

for r in all_results:
    m = r["metrics"]
    label = f"{r['company']} ({r['code']})"
    print(f"{label:14s} {m['total_return_pct']:>+7.2f}% {m['cagr_pct']:>+7.2f}% {m['sharpe_ratio']:>6.3f} {m['annual_volatility_pct']:>7.2f}% {m['max_drawdown_pct']:>7.2f}% {m['calmar_ratio']:>7.2f} {m['win_rate_pct']:>5.1f}% {m['profit_factor']:>7.2f} {m['total_trades']:>4d}")

print(f"{'-'*85}")

# 平均/综合
avg_ret = sum(m["total_return_pct"] for m in all_metrics) / len(all_metrics)
avg_sharpe = sum(m["sharpe_ratio"] for m in all_metrics) / len(all_metrics)
avg_dd = sum(m["max_drawdown_pct"] for m in all_metrics) / len(all_metrics)
avg_win = sum(m["win_rate_pct"] for m in all_metrics) / len(all_metrics)

print(f"\n  8只标的平均: 收益率={avg_ret:+.2f}% | 夏普={avg_sharpe:.3f} | 最大回撤={avg_dd:.2f}% | 胜率={avg_win:.1f}%")
print(f"\n  完整数据已保存至: {OUT_DIR}")
