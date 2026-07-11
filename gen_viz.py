import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from pathlib import Path

SIG_DIR = Path("D:/AI/线上学习/data/signals")
OUT_HTML = Path("D:/AI/线上学习/turtle_signals_viz.html")

# Load summary
with open(SIG_DIR / "_trading_summary_v2.json", "r", encoding="utf-8") as f:
    summary = json.load(f)

stocks = summary["stocks"]
stock_files = [
    ("hengrui_A_600276_signals_v2.json", "恒瑞医药", "600276", "A股", "CNY"),
    ("hengrui_HK_01276_signals_v2.json", "恒瑞医药", "01276", "港股", "HKD"),
    ("beigene_A_688235_signals_v2.json", "百济神州", "688235", "A股", "CNY"),
    ("beigene_HK_06160_signals_v2.json", "百济神州", "06160", "港股", "HKD"),
    ("beigene_US_ONC_signals_v2.json", "百济神州", "ONC", "美股", "USD"),
    ("innovent_HK_01801_signals_v2.json", "信达生物", "01801", "港股", "HKD"),
    ("junshi_A_688180_signals_v2.json", "君实生物", "688180", "A股", "CNY"),
    ("junshi_HK_01877_signals_v2.json", "君实生物", "01877", "港股", "HKD"),
]

cards = []

for sig_file, name, code, market, ccy in stock_files:
    with open(SIG_DIR / sig_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Only last 120 trading days
    plot = data[-120:]
    dates = [d["trade_date"] for d in plot]
    prices = [d["close"] for d in plot]
    p20h = [d["prev20_high"] for d in plot]
    p20l = [d["prev20_low"] for d in plot]
    ch_mid = [(h + l) / 2 if h and l else None for h, l in zip(p20h, p20l)]
    p10l = [d["prev10_low"] for d in plot]
    p10h = [d["prev10_high"] for d in plot]
    atrs = [d["atr"] for d in plot]

    # Signal coordinates
    buy_signals = [{"idx": i, "price": d["close"], "date": d["trade_date"]}
                   for i, d in enumerate(plot) if d["entry_signal"] and "做多" in str(d.get("signal_type",""))]
    sell_short_signals = [{"idx": i, "price": d["close"], "date": d["trade_date"]}
                          for i, d in enumerate(plot) if d["entry_signal"] and "做空" in str(d.get("signal_type",""))]
    exit_signals = [{"idx": i, "price": d["close"], "date": d["trade_date"], "reason": d.get("signal_type","")}
                    for i, d in enumerate(plot) if d["exit_signal"]]
    add_signals = [{"idx": i, "price": d["close"]}
                   for i, d in enumerate(plot) if d["add_signal"]]

    # Get trade history
    trades_file = SIG_DIR / sig_file.replace("signals_v2", "trades_v2")
    trades = []
    if trades_file.exists():
        with open(trades_file, "r", encoding="utf-8") as f:
            trades = json.load(f)

    cid = f"c_{code}".replace(".","_")

    # Build JS arrays for signals
    buy_js = json.dumps([{"x": s["idx"], "y": s["price"], "d": s["date"]} for s in buy_signals])
    sell_js = json.dumps([{"x": s["idx"], "y": s["price"], "d": s["date"]} for s in sell_short_signals])
    exit_js = json.dumps([{"x": s["idx"], "y": s["price"], "d": s["date"], "r": s["reason"]} for s in exit_signals])
    add_js = json.dumps([{"x": s["idx"], "y": s["price"]} for s in add_signals])

    # Get stats
    s_info = next((s for s in stocks if s["code"] == code and name in s["company"]), None)

    # Trade summary
    gains = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]

    # Build trades history rows
    trades_rows = ""
    for t in trades[-6:][::-1]:
        cls = "gain" if t["pnl_pct"] > 0 else "loss"
        trades_rows += f'<tr class="{cls}"><td>{t["entry_date"]}</td><td>{t["exit_date"]}</td><td>{"做多" if t.get("position_type")=="long" else "做空"}</td><td>{t["pnl_pct"]:+.2f}%</td><td>{t["reason"]}</td></tr>'

    cards.append(f"""
<div class="stock-card" id="{cid}">
    <div class="stock-header">
        <div>
            <span class="stock-name">{name}</span>
            <span class="stock-code">{code} · {market}</span>
            <span class="stock-ccy">{ccy}</span>
        </div>
        <div class="stock-stats">
            <div class="stat"><span class="stat-lbl">交易</span><span class="stat-val">{len(trades)}笔</span></div>
            <div class="stat"><span class="stat-lbl">胜率</span><span class="stat-val" style="color:{'#34C759' if (s_info and s_info['win_rate_pct']>40) else '#FF9500'}">{s_info["win_rate_pct"] if s_info else "?"}%</span></div>
            <div class="stat"><span class="stat-lbl">盈亏比</span><span class="stat-val">{s_info.get("profit_factor","N/A") if s_info else "N/A"}</span></div>
            <div class="stat"><span class="stat-lbl">状态</span><span class="stat-val" style="color:{'#FF3B30' if (s_info and s_info['is_in_position']) else '#888'}">{'持仓中' if (s_info and s_info['is_in_position']) else '空仓'}</span></div>
        </div>
    </div>

    <div class="legend-bar">
        <span><span class="lg-dot" style="background:#1d1d1f;"></span>收盘价</span>
        <span><span class="lg-line" style="border-color:#34C759;"></span>20日高(买入触发线)</span>
        <span><span class="lg-line" style="border-color:#FF3B30;"></span>20日低(卖出触发线)</span>
        <span><span class="lg-line" style="border-color:#888780;border-style:dashed;"></span>中轨</span>
        <span><span class="lg-line" style="border-color:rgba(255,59,48,0.3);"></span>10日低(止损线)</span>
        <span><span class="lg-badge" style="background:#34C759;color:#fff;">B</span>买入信号</span>
        <span><span class="lg-badge" style="background:#FF3B30;color:#fff;">S</span>卖出信号</span>
        <span><span class="lg-dot" style="background:#FF9500;width:10px;height:10px;border-radius:0;"></span>✕出场</span>
        <span><span class="lg-dot" style="background:#007AFF;width:8px;height:8px;"></span>加仓</span>
    </div>

    <div class="chart-box">
        <canvas id="chart_{code}" role="img" width="800" height="350"></canvas>
    </div>

    <div class="signals-summary">
        <span class="sig-buy">买入信号: {len(buy_signals)}次</span>
        <span class="sig-sell">卖出信号: {len(sell_short_signals)}次</span>
        <span class="sig-exit">出场: {len(exit_signals)}次</span>
        <span class="sig-add">加仓: {len(add_signals)}次</span>
    </div>

    <table class="trade-table">
        <thead><tr><th>入场日</th><th>出场日</th><th>方向</th><th>盈亏</th><th>原因</th></tr></thead>
        <tbody>{trades_rows}</tbody>
    </table>
</div>

<script>
(function(){{
    var ctx = document.getElementById('chart_{code}').getContext('2d');

    var buyData = {buy_js};
    var sellData = {sell_js};
    var exitData = {exit_js};
    var addData = {add_js};
    var labels = {json.dumps(dates)};

    new Chart(ctx, {{
        type: 'line',
        data: {{
            labels: labels,
            datasets: [
                {{
                    label: '收盘价',
                    data: {json.dumps(prices)},
                    borderColor: '#1d1d1f',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.2,
                    fill: false,
                    order: 1
                }},
                {{
                    label: '上轨(20日高) — 买入触发',
                    data: {json.dumps(p20h)},
                    borderColor: '#34C759',
                    borderWidth: 1.5,
                    borderDash: [6,3],
                    pointRadius: 0,
                    tension: 0.2,
                    fill: false,
                    order: 2
                }},
                {{
                    label: '下轨(20日低) — 卖出触发',
                    data: {json.dumps(p20l)},
                    borderColor: '#FF3B30',
                    borderWidth: 1.5,
                    borderDash: [6,3],
                    pointRadius: 0,
                    tension: 0.2,
                    fill: false,
                    order: 2
                }},
                {{
                    label: '中轨',
                    data: {json.dumps(ch_mid)},
                    borderColor: '#888780',
                    borderWidth: 0.5,
                    borderDash: [3,3],
                    pointRadius: 0,
                    tension: 0.2,
                    fill: false,
                    order: 2
                }},
                {{
                    label: '10日低(止损参考)',
                    data: {json.dumps(p10l)},
                    borderColor: 'rgba(255,59,48,0.25)',
                    borderWidth: 0.5,
                    borderDash: [2,2],
                    pointRadius: 0,
                    tension: 0.2,
                    fill: false,
                    order: 2
                }}
            ]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2.4,
            plugins: {{
                legend: {{ display: false }},
                tooltip: {{ mode: 'index', intersect: false, backgroundColor: 'rgba(0,0,0,0.8)', titleFont: {{size:11}}, bodyFont: {{size:11}} }}
            }},
            scales: {{
                x: {{ ticks: {{ autoSkip: true, maxTicksLimit: 8, font: {{size:10}} }}, grid: {{ display: false }} }},
                y: {{ grid: {{ color: 'rgba(0,0,0,0.06)' }}, ticks: {{ font: {{size:10}} }} }}
            }}
        }},
        plugins: [{{
            afterDraw: function(c) {{
                var ctx2 = c.ctx;
                var meta = c.getDatasetMeta(0);
                if (!meta || !meta.data) return;

                // 买入信号 - 绿色大圆点 B
                buyData.forEach(function(s) {{
                    var pt = meta.data[s.x];
                    if (!pt) return;
                    ctx2.save();
                    ctx2.beginPath();
                    ctx2.arc(pt.x, pt.y, 8, 0, 2 * Math.PI);
                    ctx2.fillStyle = '#34C759';
                    ctx2.fill();
                    ctx2.strokeStyle = '#fff';
                    ctx2.lineWidth = 2;
                    ctx2.stroke();
                    ctx2.fillStyle = '#fff';
                    ctx2.font = 'bold 9px sans-serif';
                    ctx2.textAlign = 'center';
                    ctx2.textBaseline = 'middle';
                    ctx2.fillText('B', pt.x, pt.y + 0.5);
                    ctx2.restore();
                }});

                // 卖出信号 - 红色大圆点 S
                sellData.forEach(function(s) {{
                    var pt = meta.data[s.x];
                    if (!pt) return;
                    ctx2.save();
                    ctx2.beginPath();
                    ctx2.arc(pt.x, pt.y, 8, 0, 2 * Math.PI);
                    ctx2.fillStyle = '#FF3B30';
                    ctx2.fill();
                    ctx2.strokeStyle = '#fff';
                    ctx2.lineWidth = 2;
                    ctx2.stroke();
                    ctx2.fillStyle = '#fff';
                    ctx2.font = 'bold 9px sans-serif';
                    ctx2.textAlign = 'center';
                    ctx2.textBaseline = 'middle';
                    ctx2.fillText('S', pt.x, pt.y + 0.5);
                    ctx2.restore();
                }});

                // 出场信号 - 橙色叉号 X
                exitData.forEach(function(s) {{
                    var pt = meta.data[s.x];
                    if (!pt) return;
                    ctx2.save();
                    ctx2.strokeStyle = '#FF9500';
                    ctx2.lineWidth = 2.5;
                    ctx2.beginPath();
                    ctx2.moveTo(pt.x - 6, pt.y - 6);
                    ctx2.lineTo(pt.x + 6, pt.y + 6);
                    ctx2.moveTo(pt.x + 6, pt.y - 6);
                    ctx2.lineTo(pt.x - 6, pt.y + 6);
                    ctx2.stroke();
                    ctx2.restore();
                }});

                // 加仓信号 - 蓝色小圆点
                addData.forEach(function(s) {{
                    var pt = meta.data[s.x];
                    if (!pt) return;
                    ctx2.save();
                    ctx2.beginPath();
                    ctx2.arc(pt.x, pt.y, 4, 0, 2 * Math.PI);
                    ctx2.fillStyle = '#007AFF';
                    ctx2.fill();
                    ctx2.restore();
                }});
            }}
        }}]
    }});
}})();
</script>""")

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>海龟策略可视化 — 股价·通道·买卖信号</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background:#f5f5f7; color:#1d1d1f; padding:24px; }}
h1 {{ font-size:22px; font-weight:600; margin-bottom:4px; }}
.subtitle {{ font-size:13px; color:#888; margin-bottom:24px; }}
.stock-card {{ background:#fff; border-radius:12px; border:0.5px solid rgba(0,0,0,0.1); margin-bottom:20px; padding:20px; }}
.stock-header {{ display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; margin-bottom:12px; }}
.stock-name {{ font-size:16px; font-weight:600; }}
.stock-code {{ font-size:12px; color:#888; margin-left:8px; }}
.stock-ccy {{ display:inline-block; font-size:10px; padding:1px 6px; border-radius:3px; background:#f0f0f0; color:#666; margin-left:4px; vertical-align:middle; }}
.stock-stats {{ display:flex; gap:16px; }}
.stat {{ text-align:center; }}
.stat-lbl {{ display:block; font-size:10px; color:#aaa; }}
.stat-val {{ display:block; font-size:15px; font-weight:500; }}
.legend-bar {{ display:flex; flex-wrap:wrap; gap:12px; font-size:11px; color:#666; padding:8px 0; border-bottom:0.5px solid rgba(0,0,0,0.08); margin-bottom:12px; }}
.legend-bar span {{ display:flex; align-items:center; gap:3px; }}
.lg-dot {{ display:inline-block; width:10px; height:10px; border-radius:50%; }}
.lg-line {{ display:inline-block; width:16px; height:0; border-top:2px dashed; vertical-align:middle; }}
.lg-badge {{ display:inline-flex; width:16px; height:16px; border-radius:50%; align-items:center; justify-content:center; font-size:9px; font-weight:bold; }}
.chart-box {{ width:100%; margin-bottom:12px; }}
.signals-summary {{ display:flex; gap:16px; margin-bottom:10px; font-size:12px; }}
.sig-buy {{ color:#34C759; font-weight:500; }}
.sig-sell {{ color:#FF3B30; font-weight:500; }}
.sig-exit {{ color:#FF9500; }}
.sig-add {{ color:#007AFF; }}
.trade-table {{ width:100%; border-collapse:collapse; font-size:11px; color:#555; }}
.trade-table th {{ text-align:left; padding:4px 8px; border-bottom:0.5px solid rgba(0,0,0,0.1); font-weight:500; color:#888; }}
.trade-table td {{ padding:4px 8px; border-bottom:0.5px solid rgba(0,0,0,0.04); }}
.trade-table .gain td {{ color:#34C759; }}
.trade-table .loss td {{ color:#FF3B30; }}
@media (max-width:640px) {{ .stock-stats {{ gap:8px; }} .stat-val {{ font-size:13px; }} .legend-bar {{ gap:8px; font-size:10px; }} }}
</style>
</head>
<body>
<h1>海龟策略 — 股价 · 高低价格通道 · 买卖信号</h1>
<p class="subtitle">基于近半年日线数据 · 绿色虚线=20日高点(买入触发) · 红色虚线=20日低点(卖出触发) · 🟢B=买入 🟡S=卖出 🟠✕=出场 🔵=加仓</p>
{chr(10).join(cards)}
</body>
</html>"""

with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(html)

print(f"可视化图表已生成: {OUT_HTML}")
