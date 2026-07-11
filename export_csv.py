#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Export all JSON data to CSV format.
Output: data/csv/
"""
import json, csv, os, glob

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_DIR  = os.path.join(BASE_DIR, "data", "csv")
os.makedirs(CSV_DIR, exist_ok=True)

SIG_DIR  = os.path.join(BASE_DIR, "data", "signals")
BT_DIR   = os.path.join(BASE_DIR, "data", "backtest")
IND_DIR  = os.path.join(BASE_DIR, "data", "indicators")
STD_DIR  = os.path.join(BASE_DIR, "data", "standardized")

# Stock name mapping from file prefix
STOCK_INFO = {
    "hengrui_A_600276":   ("恒瑞医药", "A股"),
    "hengrui_HK_01276":   ("恒瑞医药", "港股"),
    "beigene_A_688235":   ("百济神州", "A股"),
    "beigene_HK_06160":   ("百济神州", "港股"),
    "beigene_US_ONC":     ("百济神州", "美股"),
    "innovent_HK_01801":  ("信达生物", "港股"),
    "junshi_A_688180":    ("君实生物", "A股"),
    "junshi_HK_01877":    ("君实生物", "港股"),
}

def write_csv(path, headers, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(headers)
        for row in rows:
            w.writerow(row)
    print(f"  [OK] {os.path.relpath(path, BASE_DIR)} ({len(rows)} rows)")

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# 1. Daily signals
def export_signals():
    print("\n[1/6] Daily signals...")
    all_rows = []
    for prefix, (name, mkt) in STOCK_INFO.items():
        data = load_json(os.path.join(SIG_DIR, f"{prefix}_signals.json"))
        rows = []
        for d in data:
            rows.append([name, mkt, d["trade_date"], d["open"], d["high"], d["low"],
                        d["close"], d.get("volume",""), d.get("ma5",""), d.get("ma15",""),
                        d.get("ma_signal",""), d.get("trade_signal",""),
                        d.get("position",""), d.get("exec_note","")])
        h = ["name","market","date","open","high","low","close",
             "volume","MA5","MA15","ma_signal","trade_signal","position","note"]
        write_csv(os.path.join(CSV_DIR, f"{prefix}_signals.csv"), h, rows)
        all_rows.extend(rows)
    write_csv(os.path.join(CSV_DIR, "all_stocks_signals.csv"), h, all_rows)

# 2. Trade records
def export_trades():
    print("\n[2/6] Trade records...")
    all_rows = []
    for prefix, (name, mkt) in STOCK_INFO.items():
        data = load_json(os.path.join(SIG_DIR, f"{prefix}_trades.json"))
        rows = []
        for t in data:
            rows.append([name, mkt, t["trade_id"], t["entry_date"], t["entry_price"],
                        t["exit_date"], t["exit_price"], t["holding_days"],
                        t["pnl"], t["pnl_pct"], t["result"]])
        h = ["name","market","trade_id","entry_date","entry_price",
             "exit_date","exit_price","holding_days","pnl","pnl_pct","result"]
        write_csv(os.path.join(CSV_DIR, f"{prefix}_trades.csv"), h, rows)
        all_rows.extend(rows)
    write_csv(os.path.join(CSV_DIR, "all_stocks_trades.csv"), h, all_rows)

# 3. Equity curves
def export_equity():
    print("\n[3/6] Equity curves...")
    all_rows = []
    for prefix, (name, mkt) in STOCK_INFO.items():
        data = load_json(os.path.join(BT_DIR, f"{prefix}_equity.json"))
        rows = []
        for d in data:
            rows.append([name, mkt, d["trade_date"], d["close"], d["position"],
                        d["strategy_equity"], d["bh_equity"],
                        d["strategy_daily_ret"], d["bh_daily_ret"]])
        h = ["name","market","date","close","position",
             "strategy_equity","bh_equity","strategy_daily_ret_pct","bh_daily_ret_pct"]
        write_csv(os.path.join(CSV_DIR, f"{prefix}_equity.csv"), h, rows)
        all_rows.extend(rows)
    write_csv(os.path.join(CSV_DIR, "all_stocks_equity.csv"), h, all_rows)

# 4. Backtest summary
def export_summary():
    print("\n[4/6] Backtest summary...")
    s = load_json(os.path.join(BT_DIR, "backtest_summary.json"))["stocks"]
    h = ["name","market","code","currency",
         "strategy_total_return_pct","strategy_annual_return_pct","bh_total_return_pct","excess_return_pct",
         "strategy_max_drawdown_pct","bh_max_drawdown_pct","max_dd_duration_days",
         "strategy_volatility_pct","bh_volatility_pct","downside_volatility_pct",
         "sharpe","sortino","calmar","bh_sharpe",
         "total_trades","win_rate_pct","profit_factor","avg_win_pct","avg_loss_pct",
         "win_loss_ratio","expectancy_pct","max_consecutive_wins","max_consecutive_losses",
         "avg_holding_days","holding_ratio_pct","daily_win_rate_pct",
         "best_day_pct","worst_day_pct","final_strategy_equity","final_bh_equity"]
    rows = []
    for r in s:
        rows.append([r["name"],r["market"],r["code"],r["currency"],
                    r["strategy_total_return_pct"],r["strategy_annual_return_pct"],
                    r["bh_total_return_pct"],r["excess_return_pct"],
                    r["strategy_max_drawdown_pct"],r["bh_max_drawdown_pct"],
                    r["strategy_max_dd_duration"],
                    r["strategy_volatility_pct"],r["bh_volatility_pct"],
                    r["strategy_downside_vol_pct"],
                    r["strategy_sharpe"],r["strategy_sortino"],r["strategy_calmar"],
                    r["bh_sharpe"],
                    r["total_trades"],r["win_rate_pct"],
                    r.get("profit_factor",""),r["avg_win_pct"],r["avg_loss_pct"],
                    r.get("win_loss_ratio",""),r["expectancy_pct"],
                    r["max_consecutive_wins"],r["max_consecutive_losses"],
                    r["avg_holding_days"],r["holding_ratio_pct"],r["daily_win_rate_pct"],
                    r["best_day_pct"],r["worst_day_pct"],
                    r["final_strategy_equity"],r["final_bh_equity"]])
    write_csv(os.path.join(CSV_DIR, "backtest_summary.csv"), h, rows)

# 5. MA indicators
def export_ma():
    print("\n[5/6] MA indicators...")
    all_rows = []
    for prefix, (name, mkt) in STOCK_INFO.items():
        data = load_json(os.path.join(IND_DIR, f"{prefix}_ma.json"))
        rows = []
        for d in data:
            rows.append([name, mkt, d["trade_date"], d["open"], d["high"], d["low"],
                        d["close"], d.get("volume",""), d.get("amount",""),
                        d.get("currency",""), d.get("ma5",""), d.get("ma15",""),
                        d.get("ma_signal","")])
        h = ["name","market","date","open","high","low","close",
             "volume","amount","currency","MA5","MA15","ma_signal"]
        write_csv(os.path.join(CSV_DIR, f"{prefix}_ma.csv"), h, rows)
        all_rows.extend(rows)
    write_csv(os.path.join(CSV_DIR, "all_stocks_ma.csv"), h, all_rows)

# 6. Standardized kline
def export_std():
    print("\n[6/6] Standardized kline...")
    all_rows = []
    for prefix, (name, mkt) in STOCK_INFO.items():
        p = os.path.join(STD_DIR, f"{prefix}_std.json")
        if not os.path.exists(p):
            continue
        data = load_json(p)
        rows = []
        for d in data:
            rows.append([name, mkt, d["trade_date"], d["open"], d["high"], d["low"],
                        d["close"], d.get("volume",""), d.get("amount",""),
                        d.get("currency","")])
        h = ["name","market","date","open","high","low","close",
             "volume","amount","currency"]
        write_csv(os.path.join(CSV_DIR, f"{prefix}_std.csv"), h, rows)
        all_rows.extend(rows)
    if all_rows:
        write_csv(os.path.join(CSV_DIR, "all_stocks_std.csv"), h, all_rows)

if __name__ == "__main__":
    print(f"Output dir: {CSV_DIR}")
    export_signals()
    export_trades()
    export_equity()
    export_summary()
    export_ma()
    export_std()

    files = glob.glob(os.path.join(CSV_DIR, "*.csv"))
    total = sum(sum(1 for _ in open(f, encoding="utf-8-sig")) - 1 for f in files)
    print(f"\nDone! {len(files)} CSV files, {total:,} rows total")
