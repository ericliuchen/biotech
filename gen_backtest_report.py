import json, sys, io, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from pathlib import Path

BT_DIR = Path("D:/AI/线上学习/data/backtest")
OUT_HTML = Path("D:/AI/线上学习/backtest_report.html")

with open(BT_DIR / "_backtest_summary.json", "r", encoding="utf-8") as f:
    summary = json.load(f)

results = summary["results"]

# Generate equity curve Chart.js datasets
chart_configs = []
cards = []

for idx, r in enumerate(results):
    eq_file = BT_DIR / f"{r['company']}_{r['code']}".replace("_", "_") 
    # Find equity file
    import glob as gb
    eq_paths = list(BT_DIR.glob(f"*{r['code']}*equity*"))
    if not eq_paths:
        continue
    eq_path = eq_paths[0]

    with open(eq_path, "r", encoding="utf-8") as f:
        eq_data = json.load(f)

    # Only last 120
    eq_plot = eq_data[-120:] if len(eq_data) > 120 else eq_data
    dates = [d["date"] for d in eq_plot]
    net_values = [d["net_value"] for d in eq_plot]
    capital_line = [d["capital"] for d in eq_plot]
    nv_start = net_values[0]

    # Normalize to percentage returns
    returns_pct = [(v / nv_start - 1) * 100 for v in net_values]

    m = r["metrics"]
    cid = f"eq_{r['code']}"

    cards.append(f"""
<div class="card">
    <div class="card-header">
        <div class="card-title">{r['company']} ({r['code']} {r['market']})</div>
        <div class="card-metrics">
            <div class="cm cm-{'pos' if m['total_return_pct'] > 0 else 'neg'}">{m['total_return_pct']:+.2f}%</div>
            <div class="cm-sub">年化 {m['cagr_pct']:+.2f}%</div>
            <div class="cm-sub" style="color:#FF9500;">回撤 {m['max_drawdown_pct']:.2f}%</div>
        </div>
    </div>
    <div class="metrics-row">
        <div class="m-item"><span class="m-lbl">夏普比率</span><span class="m-val" style="color:{'#34C759' if m['sharpe_ratio'] > 0.5 else '#FF9500' if m['sharpe_ratio'] > -0.5 else '#FF3B30'}">{m['sharpe_ratio']:.3f}</span></div>
        <div class="m-item"><span class="m-lbl">年化波动</span><span class="m-val">{m['annual_volatility_pct']:.2f}%</span></div>
        <div class="m-item"><span class="m-lbl">最大回撤</span><span class="m-val" style="color:#FF3B30;">{m['max_drawdown_pct']:.2f}%</span></div>
        <div class="m-item"><span class="m-lbl">Calmar比</span><span class="m-val">{m['calmar_ratio']:.2f}</span></div>
        <div class="m-item"><span class="m-lbl">胜率</span><span class="m-val">{m['win_rate_pct']:.1f}%</span></div>
        <div class="m-item"><span class="m-lbl">盈亏比</span><span class="m-val">{m['profit_factor']:.2f}</span></div>
        <div class="m-item"><span class="m-lbl">交易笔数</span><span class="m-val">{m['total_trades']}</span></div>
        <div class="m-item"><span class="m-lbl">平均持仓</span><span class="m-val">{m['avg_hold_days']:.0f}天</span></div>
    </div>
    <div class="chart-wrap">
        <canvas id="{cid}" role="img" aria-label="Equity curve for {r['company']}"></canvas>
    </div>
</div>""")

    chart_configs.append(f"""
new Chart(document.getElementById('{cid}'), {{
    type: 'line',
    data: {{
        labels: {json.dumps(dates)},
        datasets: [
            {{
                label: '累计收益率',
                data: {json.dumps(returns_pct)},
                borderColor: '#534AB7',
                backgroundColor: 'rgba(83,74,183,0.08)',
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.2,
                fill: true
            }}
        ]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: true,
        aspectRatio: 3.5,
        plugins: {{
            legend: {{ display: false }},
            tooltip: {{
                callbacks: {{
                    label: function(ctx) {{ return ctx.parsed.y.toFixed(2) + '%'; }}
                }}
            }}
        }},
        scales: {{
            x: {{ ticks: {{ autoSkip: true, maxTicksLimit: 6, font:{{size:9}} }}, grid: {{ display: false }} }},
            y: {{
                ticks: {{ font:{{size:9}}, callback: function(v) {{ return v.toFixed(1) + '%'; }} }},
                grid: {{ color: 'rgba(0,0,0,0.04)' }}
            }}
        }}
    }}
}});""")

# Summary table rows
table_rows = ""
for r in results:
    m = r["metrics"]
    cls = "row-pos" if m['total_return_pct'] > 0 else "row-neg"
    table_rows += f"<tr class='{cls}'><td>{r['company']}</td><td>{r['code']}</td><td>{r['market']}</td>"
    table_rows += f"<td>{m['total_return_pct']:+.2f}%</td><td>{m['cagr_pct']:+.2f}%</td>"
    table_rows += f"<td>{m['sharpe_ratio']:.3f}</td><td>{m['annual_volatility_pct']:.2f}%</td>"
    table_rows += f"<td>{m['max_drawdown_pct']:.2f}%</td><td>{m['win_rate_pct']:.1f}%</td>"
    table_rows += f"<td>{m['profit_factor']:.2f}</td><td>{m['total_trades']}</td></tr>"

# Average row
avg = {k: sum(r['metrics'][k] for r in results) / len(results) for k in ['total_return_pct','cagr_pct','sharpe_ratio','annual_volatility_pct','max_drawdown_pct','win_rate_pct','total_trades']}
# Profit factor average (filter inf)
pfs = [r['metrics']['profit_factor'] for r in results if isinstance(r['metrics']['profit_factor'], (int, float)) and r['metrics']['profit_factor'] < 100]
avg_pf = sum(pfs) / len(pfs) if pfs else 0

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>海龟策略回测报告</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background:#f5f5f7; color:#1d1d1f; padding:24px; }}
h1 {{ font-size:22px; font-weight:600; margin-bottom:4px; }}
.subtitle {{ font-size:13px; color:#888; margin-bottom:24px; }}

.summary-box {{ background:#fff; border-radius:12px; border:0.5px solid rgba(0,0,0,0.1); padding:20px; margin-bottom:20px; }}
.table-wrap {{ overflow-x:auto; }}
table {{ width:100%; border-collapse:collapse; font-size:12px; }}
th {{ text-align:left; padding:8px 10px; border-bottom:1px solid rgba(0,0,0,0.1); font-weight:500; color:#666; font-size:11px; white-space:nowrap; }}
td {{ padding:7px 10px; border-bottom:0.5px solid rgba(0,0,0,0.05); white-space:nowrap; }}
.row-pos {{ background:rgba(52,199,89,0.03); }}
.row-neg td:first-child {{ color:#1d1d1f; }}
tr.avg-row {{ background:rgba(83,74,183,0.05); font-weight:500; }}
tr.avg-row td {{ border-top:1.5px solid rgba(83,74,183,0.2); }}

.card {{ background:#fff; border-radius:12px; border:0.5px solid rgba(0,0,0,0.1); margin-bottom:16px; padding:16px 20px; }}
.card-header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }}
.card-title {{ font-size:15px; font-weight:500; }}
.card-metrics {{ text-align:right; }}
.cm {{ font-size:18px; font-weight:600; }}
.cm.pos {{ color:#34C759; }} .cm.neg {{ color:#FF3B30; }}
.cm-sub {{ font-size:11px; color:#888; }}

.metrics-row {{ display:flex; flex-wrap:wrap; gap:6px 16px; margin-bottom:10px; font-size:12px; }}
.m-item {{ display:flex; gap:4px; }}
.m-lbl {{ color:#888; }}
.m-val {{ font-weight:500; }}

.chart-wrap {{ width:100%; height:120px; position:relative; }}
@media (max-width:640px) {{ .metrics-row {{ gap:4px 10px; font-size:11px; }} }}
</style>
</head>
<body>
<h1>海龟策略回测报告</h1>
<p class="subtitle">初始资金=1,000,000 · 每笔风险1% · 2ATR止损 · 0.5ATR加仓(最多4次) · 手续费0.1% · 数据: 2025.07~2026.07</p>

<div class="summary-box">
    <div class="table-wrap">
    <table>
    <thead><tr>
        <th>标的</th><th>代码</th><th>市场</th>
        <th>总收益率</th><th>年化收益</th><th>夏普比率</th><th>年化波动</th>
        <th>最大回撤</th><th>胜率</th><th>盈亏比</th><th>交易</th>
    </tr></thead>
    <tbody>
        {table_rows}
        <tr class="avg-row">
            <td><b>8只平均</b></td><td></td><td></td>
            <td><b>{avg['total_return_pct']:+.2f}%</b></td><td><b>{avg['cagr_pct']:+.2f}%</b></td>
            <td><b>{avg['sharpe_ratio']:.3f}</b></td><td><b>{avg['annual_volatility_pct']:.2f}%</b></td>
            <td><b>{avg['max_drawdown_pct']:.2f}%</b></td>
            <td><b>{avg['win_rate_pct']:.1f}%</b></td><td><b>{avg_pf:.2f}</b></td>
            <td><b>{avg['total_trades']:.0f}</b></td>
        </tr>
    </tbody>
    </table>
    </div>
</div>

<h2 style="font-size:16px;font-weight:500;margin-bottom:10px;">每条权益曲线</h2>
{chr(10).join(cards)}

<script>
{chr(10).join(chart_configs)}
</script>
</body>
</html>"""

with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(html)

print(f"回测报告已生成: {OUT_HTML}")
