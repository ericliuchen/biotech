import json
import sys
import io
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SIG_DIR = Path("D:/AI/线上学习/data/signals")
OUT_HTML = Path("D:/AI/线上学习/turtle_signals.html")

with open(SIG_DIR / "_trading_summary_v2.json", "r", encoding="utf-8") as f:
    summary = json.load(f)

stocks = summary["stocks"]
charts = []

for idx, s in enumerate(stocks):
    key_name = f"{s['company']}_{s['code']}".replace(" ", "_")
    # Determine the signal file name
    if "A股" in s["market"]:
        code_key = f"{s['company']}_A_{s['code']}" if "恒瑞" in s["company"] or "君实" in s["company"] else s['code']
    elif "美股" in s["market"]:
        code_key = "beigene_US_ONC"
    else:
        code_key = f"{s['company']}_HK_{s['code']}"
    
    # Find signal file
    sig_file = None
    for f in SIG_DIR.glob(f"*{s['code']}*signals_v2*"):
        sig_file = f
        break
    
    if not sig_file:
        continue

    with open(sig_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Take last 120 records
    plot_data = data[-120:] if len(data) > 120 else data
    dates = [d["trade_date"] for d in plot_data]

    # Price line
    closes = [d["close"] for d in plot_data]
    # Channel lines
    p20h = [d["prev20_high"] for d in plot_data]
    p20l = [d["prev20_low"] for d in plot_data]
    p10l_for_long = [d["prev10_low"] for d in plot_data]
    p10h_for_short = [d["prev10_high"] for d in plot_data]

    # Entry signals (buy/sell)
    entry_x = []
    entry_y = []
    entry_labels = []
    entry_colors = []
    for i, d in enumerate(plot_data):
        if d["entry_signal"]:
            entry_x.append(i)
            entry_y.append(d["close"])
            typ = d["signal_type"]
            if "做多" in str(typ):
                entry_labels.append("B")
                entry_colors.append("#34C759")
            else:
                entry_labels.append("S")
                entry_colors.append("#FF3B30")

    # Exit signals
    exit_x = []
    exit_y = []
    exit_labels = []
    for i, d in enumerate(plot_data):
        if d["exit_signal"]:
            exit_x.append(i)
            exit_y.append(d["close"])
            exit_labels.append("X")

    # Add signals
    add_x = []
    add_y = []
    for i, d in enumerate(plot_data):
        if d["add_signal"]:
            add_x.append(i)
            add_y.append(d["close"])

    label = f"{s['company']} ({s['code']} {s['market']})"
    cid = f"chart_{idx}"

    # Build trade history
    trades_file = sig_file.parent / sig_file.name.replace("signals_v2", "trades_v2")
    trades_list = []
    if trades_file.exists():
        with open(trades_file, "r", encoding="utf-8") as f:
            trades_list = json.load(f)

    trades_html = '<div class="trades">'
    for t in trades_list[-5:]:
        color = "#34C759" if t["pnl_pct"] > 0 else "#FF3B30"
        direction = "做多" if t.get("position_type") == "long" else "做空"
        trades_html += f'<div class="trade-item">'
        trades_html += f'<span class="trade-dir">{direction}</span> '
        trades_html += f'{t["entry_date"]} → {t["exit_date"]} '
        trades_html += f'<span style="color:{color};font-weight:500;">{t["pnl_pct"]:+.2f}%</span> '
        trades_html += f'<span class="trade-reason">{t["reason"]}</span>'
        trades_html += f'</div>'
    trades_html += '</div>'

    charts.append(f"""
<div class="card">
    <div class="card-header">
        <div class="card-title">{label}</div>
        <div class="card-stats">
            <span>交易 {s["completed_trades"]}笔</span>
            <span>胜率 <b>{s["win_rate_pct"]}%</b></span>
            <span>做多 {s["long_signals"]}次</span>
            <span>做空 {s["short_signals"]}次</span>
            <span class="{'pos-y' if s['is_in_position'] else 'pos-n'}">{'【持仓中】' if s['is_in_position'] else '空仓'}</span>
        </div>
    </div>
    <div class="chart-wrap">
        <canvas id="{cid}" role="img" aria-label="Turtle trading signals for {label}"></canvas>
    </div>
    {trades_html}
</div>""")

    # Build entry/exit markers
    entry_markers = "[" + ",".join(
        f'{{x:{i},y:{y},label:"{l}",color:"{c}"}}'
        for i, y, l, c in zip(entry_x, entry_y, entry_labels, entry_colors)
    ) + "]"
    exit_markers = "[" + ",".join(
        f'{{x:{i},y:{y}}}' for i, y in zip(exit_x, exit_y)
    ) + "]"
    add_markers = "[" + ",".join(
        f'{{x:{i},y:{y}}}' for i, y in zip(add_x, add_y)
    ) + "]"

    charts.append(f"""
<script>
(function() {{
    var entries = {entry_markers};
    var exits = {exit_markers};
    var adds = {add_markers};
    var origLabels = {json.dumps(dates)};

    var chart = new Chart(document.getElementById('{cid}'), {{
        type: 'line',
        data: {{
            labels: origLabels,
            datasets: [
                {{
                    label: '收盘价',
                    data: {json.dumps(closes)},
                    borderColor: '#1d1d1f',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    tension: 0.2,
                    fill: false
                }},
                {{
                    label: '20日高点 (做多触发线)',
                    data: {json.dumps(p20h)},
                    borderColor: '#34C759',
                    borderWidth: 1,
                    borderDash: [5,3],
                    pointRadius: 0,
                    tension: 0.2,
                    fill: false
                }},
                {{
                    label: '20日低点 (做空触发线)',
                    data: {json.dumps(p20l)},
                    borderColor: '#FF3B30',
                    borderWidth: 1,
                    borderDash: [5,3],
                    pointRadius: 0,
                    tension: 0.2,
                    fill: false
                }},
                {{
                    label: '10日低点 (止损线)',
                    data: {json.dumps(p10l_for_long)},
                    borderColor: 'rgba(255,59,48,0.3)',
                    borderWidth: 0.5,
                    borderDash: [2,2],
                    pointRadius: 0,
                    tension: 0.2,
                    fill: false
                }}
            ]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{ display: true, position: 'bottom', labels: {{ boxWidth: 10, padding: 10, font: {{size:10}} }} }},
                tooltip: {{ mode: 'index', intersect: false }},
                annotation: {{}}
            }},
            scales: {{
                x: {{ ticks: {{ autoSkip: true, maxTicksLimit: 8, maxRotation: 0 }}, grid: {{ display: false }} }},
                y: {{ grid: {{ color: 'rgba(0,0,0,0.05)' }} }}
            }}
        }},
        plugins: [{{
            afterDraw: function(c) {{
                var ctx = c.ctx;
                var meta = c.getDatasetMeta(0);

                // Entry markers
                entries.forEach(function(e) {{
                    var pt = meta.data[Math.round(e.x)];
                    if (!pt) return;
                    ctx.save();
                    ctx.beginPath();
                    ctx.arc(pt.x, pt.y, 7, 0, 2 * Math.PI);
                    ctx.fillStyle = e.color;
                    ctx.fill();
                    ctx.fillStyle = '#fff';
                    ctx.font = 'bold 9px sans-serif';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(e.label, pt.x, pt.y);
                    ctx.restore();
                }});

                // Exit markers
                exits.forEach(function(e) {{
                    var pt = meta.data[Math.round(e.x)];
                    if (!pt) return;
                    ctx.save();
                    ctx.beginPath();
                    ctx.moveTo(pt.x-5, pt.y-5);
                    ctx.lineTo(pt.x+5, pt.y+5);
                    ctx.moveTo(pt.x+5, pt.y-5);
                    ctx.lineTo(pt.x-5, pt.y+5);
                    ctx.strokeStyle = '#FF9500';
                    ctx.lineWidth = 2;
                    ctx.stroke();
                    ctx.restore();
                }});

                // Add markers
                adds.forEach(function(e) {{
                    var pt = meta.data[Math.round(e.x)];
                    if (!pt) return;
                    ctx.save();
                    ctx.beginPath();
                    ctx.arc(pt.x, pt.y, 4, 0, 2 * Math.PI);
                    ctx.fillStyle = '#007AFF';
                    ctx.fill();
                    ctx.restore();
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
<title>海龟策略交易信号 - 创新药企</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f7; color: #1d1d1f; padding: 24px; }}
h1 {{ font-size: 22px; font-weight: 600; margin-bottom: 4px; }}
.subtitle {{ font-size: 13px; color: #888; margin-bottom: 24px; }}
.card {{ background: #fff; border-radius: 12px; border: 0.5px solid rgba(0,0,0,0.1); margin-bottom: 20px; overflow: hidden; }}
.card-header {{ display: flex; justify-content: space-between; align-items: center; padding: 16px 20px 0; flex-wrap: wrap; gap: 8px; }}
.card-title {{ font-size: 15px; font-weight: 500; }}
.card-stats {{ display: flex; gap: 12px; font-size: 12px; color: #666; flex-wrap: wrap; }}
.card-stats b {{ font-weight: 500; }}
.pos-y {{ color:#34C759; font-weight:500; }}
.pos-n {{ color:#888; }}
.chart-wrap {{ position: relative; width: 100%; height: 320px; padding: 12px 20px; }}
.trades {{ padding: 0 20px 16px; font-size: 12px; }}
.trade-item {{ padding: 4px 0; color: #555; border-bottom: 0.5px solid rgba(0,0,0,0.05); }}
.trade-dir {{ display: inline-block; width: 28px; font-size: 11px; color: #888; }}
.trade-reason {{ font-size: 10px; color: #aaa; margin-left: 4px; }}
.legend-guide {{ display: flex; flex-wrap: wrap; gap: 16px; font-size: 12px; color: #666; margin-bottom: 16px; padding: 12px 0; border-bottom: 0.5px solid rgba(0,0,0,0.08); }}
.legend-guide span {{ display: flex; align-items: center; gap: 4px; }}
.dot {{ width: 14px; height: 14px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 8px; font-weight: bold; color: #fff; }}
@media (max-width:640px) {{ .card-stats {{ font-size: 11px; gap: 8px; }} }}
</style>
</head>
<body>

<h1>海龟策略交易信号</h1>
<p class="subtitle">入场: 突破20日通道 · 出场: 跌破10日通道 / 2ATR止损 · 加仓: 每0.5ATR · 数据至 2026-07-10</p>

<div class="legend-guide">
    <span><span class="dot" style="background:#34C759;font-size:8px;">B</span> 做多入场</span>
    <span><span class="dot" style="background:#FF3B30;font-size:8px;">S</span> 做空入场</span>
    <span><span style="color:#FF9500;">✕</span> 出场</span>
    <span><span class="dot" style="background:#007AFF;width:8px;height:8px;"></span> 加仓</span>
    <span><span style="border-bottom:2px dashed #34C759;">—</span> 20日高(做多线)</span>
    <span><span style="border-bottom:2px dashed #FF3B30;">—</span> 20日低(做空线)</span>
    <span><span style="border-bottom:1px dashed rgba(255,59,48,0.3);">—</span> 10日低(止损线)</span>
</div>

{chr(10).join(charts)}

</body>
</html>"""

with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(html)

    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    print(f"信号图表已生成: {OUT_HTML}")
