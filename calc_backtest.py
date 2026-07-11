#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MA(5)/MA(15) 交叉策略全面量化回测。

计算指标:
  收益类: 总收益率, 年化收益率, 买入持有收益率, 超额收益
  风险类: 最大回撤, 最大回撤持续期, 年化波动率, 下行波动率
  风险调整: 夏普比率, 索提诺比率, 卡玛比率
  交易类: 胜率, 盈亏比(利润因子), 平均盈亏, 期望值, 最大连胜/连亏, 平均持仓
  日线类: 日胜率, 最大单日涨跌

输出:
  data/backtest/backtest_summary.json   — 全标的量化指标汇总
  data/backtest/{stock}_equity.json     — 每日净值曲线
  backtest_report.html                  — 可视化报告
"""
import json
import os
import math
from datetime import datetime

BASE_DIR  = r"D:\AI\线上学习"
SIG_DIR   = os.path.join(BASE_DIR, "data", "signals")
BT_DIR    = os.path.join(BASE_DIR, "data", "backtest")

# ── 参数 ──
INITIAL_CAPITAL = 10000.0   # 初始资金 (各标的统一)
RISK_FREE_RATE  = 0.02      # 无风险利率 (年化, 用于夏普/索提诺)
TRADING_DAYS    = 252       # 年化交易日

# ── 读取数据 ──
with open(os.path.join(SIG_DIR, "signal_summary.json"), "r", encoding="utf-8") as f:
    summary = json.load(f)

NAME_MAP = {
    ("恒瑞医药", "A股"): "hengrui_A_600276",
    ("恒瑞医药", "港股"): "hengrui_HK_01276",
    ("百济神州", "美股"): "beigene_US_ONC",
    ("百济神州", "港股"): "beigene_HK_06160",
    ("百济神州", "A股"): "beigene_A_688235",
    ("信达生物", "港股"): "innovent_HK_01801",
    ("君实生物", "港股"): "junshi_HK_01877",
    ("君实生物", "A股"): "junshi_A_688180",
}


def load_stock_signals(stock_info):
    """加载单标的的信号数据"""
    prefix = NAME_MAP.get((stock_info["name"], stock_info["market"]), "")
    path = os.path.join(SIG_DIR, f"{prefix}_signals.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_stock_trades(stock_info):
    """加载单标的交易记录"""
    prefix = NAME_MAP.get((stock_info["name"], stock_info["market"]), "")
    path = os.path.join(SIG_DIR, f"{prefix}_trades.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ═══════════════════════════════════════════════════════
#  净值曲线计算
# ═══════════════════════════════════════════════════════

def calc_equity_curve(signals):
    """
    计算策略净值曲线和买入持有净值曲线。
    策略: 持仓日按收盘价计算涨跌, 空仓日收益为0
    买入持有: 首日买入, 持有到最后
    
    返回: list of {date, strategy_equity, bh_equity, strategy_daily_ret, bh_daily_ret, position}
    """
    curve = []
    strategy_equity = INITIAL_CAPITAL
    bh_equity = INITIAL_CAPITAL
    
    for i, rec in enumerate(signals):
        date = rec["trade_date"]
        close = rec["close"]
        in_position = (rec["position"] == "持仓")
        
        if i == 0:
            # 首日
            strategy_daily_ret = 0.0
            bh_daily_ret = 0.0
        else:
            prev_close = signals[i-1]["close"]
            price_ret = (close / prev_close - 1) if prev_close > 0 else 0.0
            # 策略: 持仓时才有收益
            strategy_daily_ret = price_ret if in_position else 0.0
            # 买入持有: 始终有收益
            bh_daily_ret = price_ret
        
        strategy_equity *= (1 + strategy_daily_ret)
        bh_equity *= (1 + bh_daily_ret)
        
        curve.append({
            "trade_date": date,
            "close": close,
            "position": "持仓" if in_position else "空仓",
            "strategy_equity": round(strategy_equity, 2),
            "bh_equity": round(bh_equity, 2),
            "strategy_daily_ret": round(strategy_daily_ret * 100, 4),   # 百分比
            "bh_daily_ret": round(bh_daily_ret * 100, 4),
        })
    
    return curve


# ═══════════════════════════════════════════════════════
#  风险指标计算
# ═══════════════════════════════════════════════════════

def calc_max_drawdown(equity_values):
    """
    计算最大回撤及持续期。
    返回: (max_dd_pct, max_dd_duration_days, peak_date, trough_date, recovery_date)
    """
    peak = equity_values[0]
    peak_idx = 0
    max_dd = 0.0
    max_dd_start = 0
    max_dd_trough = 0
    max_dd_end = 0
    
    for i, eq in enumerate(equity_values):
        if eq > peak:
            peak = eq
            peak_idx = i
        dd = (peak - eq) / peak if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd
            max_dd_start = peak_idx
            max_dd_trough = i
            max_dd_end = i  # 暂存, 后面找恢复点
    
    # 找恢复点
    trough_eq = equity_values[max_dd_trough]
    recovery_idx = None
    for i in range(max_dd_trough + 1, len(equity_values)):
        if equity_values[i] >= equity_values[max_dd_start]:
            recovery_idx = i
            break
    
    max_dd_duration = recovery_idx - max_dd_start if recovery_idx else len(equity_values) - 1 - max_dd_start
    
    return {
        "max_dd_pct": round(max_dd * 100, 2),
        "max_dd_duration_days": max_dd_duration,
        "peak_idx": max_dd_start,
        "trough_idx": max_dd_trough,
        "recovery_idx": recovery_idx,
    }


def calc_volatility(daily_returns):
    """计算年化波动率"""
    if len(daily_returns) < 2:
        return 0.0
    mean_ret = sum(daily_returns) / len(daily_returns)
    variance = sum((r - mean_ret) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
    daily_vol = math.sqrt(variance)
    return daily_vol * math.sqrt(TRADING_DAYS) * 100  # 转百分比


def calc_downside_volatility(daily_returns):
    """计算下行波动率 (只考虑负收益)"""
    neg_returns = [r for r in daily_returns if r < 0]
    if len(neg_returns) < 2:
        return 0.0
    mean_neg = sum(neg_returns) / len(neg_returns)
    variance = sum((r - mean_neg) ** 2 for r in neg_returns) / (len(neg_returns) - 1)
    daily_vol = math.sqrt(variance)
    return daily_vol * math.sqrt(TRADING_DAYS) * 100


def calc_sharpe(daily_returns, rf_annual=RISK_FREE_RATE):
    """计算夏普比率"""
    if len(daily_returns) < 2:
        return 0.0
    rf_daily = rf_annual / TRADING_DAYS
    excess_returns = [r - rf_daily for r in daily_returns]
    mean_excess = sum(excess_returns) / len(excess_returns)
    
    variance = sum((r - mean_excess) ** 2 for r in excess_returns) / (len(excess_returns) - 1)
    std = math.sqrt(variance) if variance > 0 else 0
    
    if std == 0:
        return 0.0
    sharpe = (mean_excess / std) * math.sqrt(TRADING_DAYS)
    return round(sharpe, 3)


def calc_sortino(daily_returns, rf_annual=RISK_FREE_RATE):
    """计算索提诺比率"""
    if len(daily_returns) < 2:
        return 0.0
    rf_daily = rf_annual / TRADING_DAYS
    excess_returns = [r - rf_daily for r in daily_returns]
    mean_excess = sum(excess_returns) / len(excess_returns)
    
    neg_returns = [r for r in excess_returns if r < 0]
    if len(neg_returns) < 2:
        return 0.0
    downside_var = sum(r ** 2 for r in neg_returns) / len(neg_returns)
    downside_std = math.sqrt(downside_var) if downside_var > 0 else 0
    
    if downside_std == 0:
        return 0.0
    sortino = (mean_excess / downside_std) * math.sqrt(TRADING_DAYS)
    return round(sortino, 3)


def calc_calmar(annual_ret, max_dd_pct):
    """计算卡玛比率"""
    if max_dd_pct == 0:
        return 0.0
    return round(annual_ret / max_dd_pct, 3)


# ═══════════════════════════════════════════════════════
#  交易指标计算
# ═══════════════════════════════════════════════════════

def calc_trade_metrics(trades):
    """计算交易层面指标"""
    closed = [t for t in trades if t["result"] != "未平仓"]
    
    if not closed:
        return {
            "win_rate": 0, "profit_factor": 0, "avg_win_pct": 0,
            "avg_loss_pct": 0, "win_loss_ratio": 0, "expectancy_pct": 0,
            "max_consecutive_wins": 0, "max_consecutive_losses": 0,
            "avg_holding_days": 0,
        }
    
    wins = [t for t in closed if t["pnl"] > 0]
    losses = [t for t in closed if t["pnl"] < 0]
    
    total_win_pnl = sum(t["pnl"] for t in wins)
    total_loss_pnl = abs(sum(t["pnl"] for t in losses))
    profit_factor = round(total_win_pnl / total_loss_pnl, 3) if total_loss_pnl > 0 else float('inf')
    
    avg_win = round(sum(t["pnl_pct"] for t in wins) / len(wins), 2) if wins else 0
    avg_loss = round(sum(t["pnl_pct"] for t in losses) / len(losses), 2) if losses else 0
    
    win_loss_ratio = round(abs(avg_win / avg_loss), 3) if avg_loss != 0 else float('inf')
    
    # 期望值 = 胜率 × 平均盈利 - 亏率 × 平均亏损
    win_rate = len(wins) / len(closed)
    loss_rate = len(losses) / len(closed)
    expectancy = round(win_rate * avg_win - loss_rate * abs(avg_loss), 2)
    
    # 最大连胜/连亏
    max_consec_win = 0
    max_consec_loss = 0
    current_win = 0
    current_loss = 0
    for t in closed:
        if t["pnl"] > 0:
            current_win += 1
            current_loss = 0
            max_consec_win = max(max_consec_win, current_win)
        elif t["pnl"] < 0:
            current_loss += 1
            current_win = 0
            max_consec_loss = max(max_consec_loss, current_loss)
    
    avg_hold = round(sum(t["holding_days"] for t in closed) / len(closed), 1)
    
    return {
        "win_rate_pct": round(win_rate * 100, 1),
        "profit_factor": profit_factor if profit_factor != float('inf') else None,
        "avg_win_pct": avg_win,
        "avg_loss_pct": avg_loss,
        "win_loss_ratio": win_loss_ratio if win_loss_ratio != float('inf') else None,
        "expectancy_pct": expectancy,
        "max_consecutive_wins": max_consec_win,
        "max_consecutive_losses": max_consec_loss,
        "avg_holding_days": avg_hold,
        "total_trades": len(closed),
        "win_trades": len(wins),
        "loss_trades": len(losses),
    }


# ═══════════════════════════════════════════════════════
#  主回测函数
# ═══════════════════════════════════════════════════════

def backtest_single_stock(stock_info):
    """对单标的进行完整回测"""
    signals = load_stock_signals(stock_info)
    trades = load_stock_trades(stock_info)
    
    # 1. 净值曲线
    equity_curve = calc_equity_curve(signals)
    
    # 2. 策略日收益率序列
    strat_rets = [d["strategy_daily_ret"] / 100 for d in equity_curve]
    bh_rets = [d["bh_daily_ret"] / 100 for d in equity_curve]
    
    # 3. 总收益率
    final_strat_eq = equity_curve[-1]["strategy_equity"]
    final_bh_eq = equity_curve[-1]["bh_equity"]
    
    strat_total_ret = (final_strat_eq / INITIAL_CAPITAL - 1) * 100
    bh_total_ret = (final_bh_eq / INITIAL_CAPITAL - 1) * 100
    
    # 4. 年化收益率
    n_days = len(equity_curve)
    years = n_days / TRADING_DAYS
    strat_annual = ((final_strat_eq / INITIAL_CAPITAL) ** (1 / years) - 1) * 100 if years > 0 else 0
    bh_annual = ((final_bh_eq / INITIAL_CAPITAL) ** (1 / years) - 1) * 100 if years > 0 else 0
    
    # 5. 超额收益
    excess_ret = strat_total_ret - bh_total_ret
    
    # 6. 最大回撤
    strat_eq_values = [d["strategy_equity"] for d in equity_curve]
    bh_eq_values = [d["bh_equity"] for d in equity_curve]
    strat_dd = calc_max_drawdown(strat_eq_values)
    bh_dd = calc_max_drawdown(bh_eq_values)
    
    # 7. 波动率
    strat_vol = calc_volatility(strat_rets)
    bh_vol = calc_volatility(bh_rets)
    strat_downside_vol = calc_downside_volatility(strat_rets)
    
    # 8. 夏普/索提诺/卡玛
    strat_sharpe = calc_sharpe(strat_rets)
    strat_sortino = calc_sortino(strat_rets)
    strat_calmar = calc_calmar(strat_annual, strat_dd["max_dd_pct"])
    bh_sharpe = calc_sharpe(bh_rets)
    
    # 9. 交易指标
    trade_metrics = calc_trade_metrics(trades)
    
    # 10. 日线指标
    strat_pos_days = sum(1 for r in strat_rets if r > 0)
    strat_neg_days = sum(1 for r in strat_rets if r < 0)
    strat_zero_days = sum(1 for r in strat_rets if r == 0)
    best_day = max(strat_rets) * 100 if strat_rets else 0
    worst_day = min(strat_rets) * 100 if strat_rets else 0
    daily_win_rate = round(strat_pos_days / (strat_pos_days + strat_neg_days) * 100, 1) if (strat_pos_days + strat_neg_days) > 0 else 0
    
    # 持仓时间占比
    holding_days = sum(1 for d in equity_curve if d["position"] == "持仓")
    holding_ratio = round(holding_days / n_days * 100, 1)
    
    return {
        # 基本信息
        "name": stock_info["name"],
        "market": stock_info["market"],
        "code": stock_info["code"],
        "currency": stock_info["currency"],
        "n_days": n_days,
        "holding_ratio_pct": holding_ratio,
        
        # 收益指标
        "strategy_total_return_pct": round(strat_total_ret, 2),
        "strategy_annual_return_pct": round(strat_annual, 2),
        "bh_total_return_pct": round(bh_total_ret, 2),
        "bh_annual_return_pct": round(bh_annual, 2),
        "excess_return_pct": round(excess_ret, 2),
        
        # 风险指标
        "strategy_max_drawdown_pct": strat_dd["max_dd_pct"],
        "strategy_max_dd_duration": strat_dd["max_dd_duration_days"],
        "bh_max_drawdown_pct": bh_dd["max_dd_pct"],
        "strategy_volatility_pct": round(strat_vol, 2),
        "bh_volatility_pct": round(bh_vol, 2),
        "strategy_downside_vol_pct": round(strat_downside_vol, 2),
        
        # 风险调整收益
        "strategy_sharpe": strat_sharpe,
        "strategy_sortino": strat_sortino,
        "strategy_calmar": strat_calmar,
        "bh_sharpe": bh_sharpe,
        
        # 交易指标
        **trade_metrics,
        
        # 日线指标
        "daily_win_rate_pct": daily_win_rate,
        "best_day_pct": round(best_day, 2),
        "worst_day_pct": round(worst_day, 2),
        "positive_days": strat_pos_days,
        "negative_days": strat_neg_days,
        "flat_days": strat_zero_days,
        
        # 最终净值
        "final_strategy_equity": round(final_strat_eq, 2),
        "final_bh_equity": round(final_bh_eq, 2),
        
        # 净值曲线
        "equity_curve": equity_curve,
    }


def main():
    os.makedirs(BT_DIR, exist_ok=True)
    
    all_results = []
    
    for stock in summary["stocks"]:
        label = f"{stock['name']}({stock['market']})"
        print(f"\n{'='*60}")
        print(f"回测: {label}  代码: {stock['code']}")
        print(f"{'='*60}")
        
        result = backtest_single_stock(stock)
        all_results.append(result)
        
        # 打印关键指标
        print(f"  ── 收益指标 ──")
        print(f"  策略总收益: {result['strategy_total_return_pct']:+.2f}%  年化: {result['strategy_annual_return_pct']:+.2f}%")
        print(f"  买入持有收益: {result['bh_total_return_pct']:+.2f}%  年化: {result['bh_annual_return_pct']:+.2f}%")
        print(f"  超额收益: {result['excess_return_pct']:+.2f}%")
        print(f"  最终净值: 策略={result['final_strategy_equity']:.0f}  基准={result['final_bh_equity']:.0f}")
        
        print(f"\n  ── 风险指标 ──")
        print(f"  最大回撤: 策略={result['strategy_max_drawdown_pct']:.2f}%  基准={result['bh_max_drawdown_pct']:.2f}%")
        print(f"  回撤持续: {result['strategy_max_dd_duration']} 天")
        print(f"  年化波动率: 策略={result['strategy_volatility_pct']:.2f}%  基准={result['bh_volatility_pct']:.2f}%")
        
        print(f"\n  ── 风险调整 ──")
        print(f"  夏普比率: 策略={result['strategy_sharpe']}  基准={result['bh_sharpe']}")
        print(f"  索提诺比率: {result['strategy_sortino']}")
        print(f"  卡玛比率: {result['strategy_calmar']}")
        
        print(f"\n  ── 交易指标 ──")
        print(f"  胜率: {result['win_rate_pct']}%  交易: {result['total_trades']}笔")
        pf = result.get('profit_factor')
        print(f"  利润因子: {pf if pf else 'N/A'}")
        print(f"  平均盈利: +{result['avg_win_pct']}%  平均亏损: {result['avg_loss_pct']}%")
        wlr = result.get('win_loss_ratio')
        print(f"  盈亏比: {wlr if wlr else 'N/A'}")
        print(f"  期望值: {result['expectancy_pct']}%/笔")
        print(f"  最大连胜: {result['max_consecutive_wins']}  最大连亏: {result['max_consecutive_losses']}")
        print(f"  平均持仓: {result['avg_holding_days']}天  持仓占比: {result['holding_ratio_pct']}%")
        
        print(f"\n  ── 日线指标 ──")
        print(f"  日胜率: {result['daily_win_rate_pct']}%  (涨{result['positive_days']}/跌{result['negative_days']}/平{result['flat_days']})")
        print(f"  最佳单日: +{result['best_day_pct']}%  最差单日: {result['worst_day_pct']}%")
    
    # ── 保存汇总 ──
    summary_path = os.path.join(BT_DIR, "backtest_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        # 不保存 equity_curve 在 summary 中, 单独存
        summary_results = [{k: v for k, v in r.items() if k != "equity_curve"} for r in all_results]
        json.dump({
            "meta": {
                "description": "8个标的 MA(5)/MA(15) 交叉策略全面量化回测",
                "strategy": "MA金叉买入, MA死叉卖出, 次日开盘价执行, 单仓不做空",
                "initial_capital": INITIAL_CAPITAL,
                "risk_free_rate": RISK_FREE_RATE,
                "trading_days_per_year": TRADING_DAYS,
                "period": f"{all_results[0]['equity_curve'][0]['trade_date']} ~ {all_results[0]['equity_curve'][-1]['trade_date']}",
                "generated": "2026-07-11",
            },
            "stocks": summary_results,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n{'='*60}")
    print(f"汇总报告 → {summary_path}")
    
    # ── 保存每个标的的净值曲线 ──
    for r in all_results:
        prefix = NAME_MAP.get((r["name"], r["market"]), "")
        eq_path = os.path.join(BT_DIR, f"{prefix}_equity.json")
        with open(eq_path, "w", encoding="utf-8") as f:
            json.dump(r["equity_curve"], f, ensure_ascii=False, indent=2)
    
    # ── 汇总表 ──
    print(f"\n{'='*60}")
    print(f"{'标的':<10} {'市场':<5} {'策略收益':>8} {'基准收益':>8} {'超额':>8} {'最大回撤':>8} {'夏普':>6} {'索提诺':>6} {'卡玛':>6} {'胜率':>6} {'利润因子':>8}")
    print("─" * 110)
    for r in all_results:
        pf = r.get('profit_factor')
        pf_str = f"{pf:.3f}" if pf else "N/A"
        print(f"{r['name']:<10} {r['market']:<5} {r['strategy_total_return_pct']:>+7.2f}% {r['bh_total_return_pct']:>+7.2f}% {r['excess_return_pct']:>+7.2f}% {r['strategy_max_drawdown_pct']:>7.2f}% {r['strategy_sharpe']:>6.2f} {r['strategy_sortino']:>6.2f} {r['strategy_calmar']:>6.2f} {r['win_rate_pct']:>5.1f}% {pf_str:>8}")
    
    return all_results


if __name__ == "__main__":
    all_results = main()
