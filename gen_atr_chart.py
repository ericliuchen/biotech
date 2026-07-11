import json
from pathlib import Path

STD_DIR = Path("D:/AI/线上学习/data/standardized")
ATR_DIR = Path("D:/AI/线上学习/data/atr")
CH_DIR = Path("D:/AI/线上学习/data/channels")
OUT_HTML = Path("D:/AI/线上学习/atr_indicators.html")

with open(ATR_DIR / "_atr_summary.json", "r", encoding="utf-8") as f:
    atr_sum = json.load(f)

stocks = atr_sum["stocks"]
charts = []

for idx, s in enumerate(stocks):
    key = s["file"].replace("_atr.json", "")
    atr_file = ATR_DIR / s["file"]
    ch_file = CH_DIR / f"{key}_channel.json"

    with open(atr_file, "r", encoding="utf-8") as f:
        atr_data = json.load(f)

    # Read channel data
    ch_data_raw = []
    try:
        with open(ch_file, "r", encoding="utf-8") as f:
            ch_data_raw = json.load(f)
    except:
        pass

    # Take last 120 records
    plot_data = atr_data[-120:] if len(atr_data) > 120 else atr_data
    ch_plot = ch_data_raw[-120:] if len(ch_data_raw) > 120 else ch_data_raw

    dates = [d["trade_date"] for d in plot_data]
    prices = [d["close"] for d in plot_data]
    atr_vals = [d["atr"] for d in plot_data]
    tr_vals = [d["true_range"] for d in plot_data]
    ch_upper = [d.get("channel_upper") for d in ch_plot] if ch_plot else []
    ch_lower = [d.get("channel_lower") for d in ch_plot] if ch_plot else []

    label = f"{s['company']} ({s['code']} {s['market']})"

    # Compute stop loss levels
    atr_val = s['latest_atr']
    close_val = s['latest_close']
    stop_2atr = round(close_val - 2 * atr_val, 2) if atr_val and close_val else 0
    add_step = round(0.5 * atr_val, 4) if atr_val else 0

    chart_id = f"chart_{idx}"

    charts.append(f"""
<div class="card">
    <div class="card-header">
        <div class="card-title">{label}</div>
        <div class="card-tags">
            <span class="tag">ATR({atr_sum['period']}) = {s['latest_atr']:.2f}</span>
            <span class="tag">ATR% = {s['atr_pct']:.2f}%</span>
            <span class="tag trend-{s['atr_trend']}">{s['atr_trend']} ↗{s['atr_change_5d_pct']:+.1f}%</span>
        </div>
    </div>
    <div class="card-body">
        <div class="metric-grid">
            <div class="metric">
                <div class="metric-label">2 ATR 止损位</div>
                <div class="metric-value">{stop_2atr:.2f}</div>
                <div class="metric-sub">入场价 - 2 × ATR</div>
            </div>
            <div class="metric">
                <div class="metric-label">加仓间距</div>
                <div class="metric-value">{add_step:.2f}</div>
                <div class="metric-sub">每 0.5 ATR 加仓一次</div>
            </div>
            <div class="metric">
                <div class="metric-label">单笔风险（1%账户）</div>
                <div class="metric-value">{(2 * atr_val * 100 / close_val):.2f}%</div>
                <div class="metric-sub">股价 × 持有量</div>
            </div>
            <div class="metric">
                <div class="metric-label">浮盈保本线</div>
                <div class="metric-value">{(10 * atr_val):.2f}</div>
                <div class="metric-sub">浮盈 ≥10 ATR 后移动止损</div>
            </div>
        </div>
        <div class="chart-wrap">
            <canvas id="{chart_id}" role="img" aria-label="ATR and price chart for {label}"></canvas>
        </div>
    </div>
</div>""")

    # Build chart config as JS
    charts.append(f"""
<script>
new Chart(document.getElementById('{chart_id}'), {{
    type: 'line',
    data: {{
        labels: {json.dumps(dates)},
        datasets: [
            {{
                label: '收盘价',
                data: {json.dumps(prices)},
                yAxisID: 'y_price',
                borderColor: '#D85A30',
                borderWidth: 1.5,
                pointRadius: 0,
                tension: 0.2
            }},
            {{
                label: 'ATR(20)',
                data: {json.dumps(atr_vals)},
                yAxisID: 'y_atr',
                borderColor: '#534AB7',
                backgroundColor: 'rgba(83,74,183,0.08)',
                borderWidth: 1.5,
                pointRadius: 0,
                tension: 0.2,
                fill: true
            }},
            {{
                label: 'TR (日波幅)',
                data: {json.dumps(tr_vals)},
                yAxisID: 'y_atr',
                borderColor: 'rgba(83,74,183,0.2)',
                backgroundColor: 'rgba(83,74,183,0.04)',
                borderWidth: 0.5,
                pointRadius: 0,
                tension: 0.1,
                fill: false
            }}
        ]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            legend: {{ display: true, position: 'bottom', labels: {{ boxWidth: 12, padding: 12, font: {{ size: 11 }} }} }},
            tooltip: {{ mode: 'index', intersect: false }}
        }},
        scales: {{
            x: {{ ticks: {{ autoSkip: true, maxTicksLimit: 8, maxRotation: 0 }}, grid: {{ display: false }} }},
            y_price: {{
                position: 'left',
                title: {{ display: true, text: '价格', font: {{ size: 11 }} }},
                grid: {{ color: 'rgba(0,0,0,0.05)' }}
            }},
            y_atr: {{
                position: 'right',
                title: {{ display: true, text: 'ATR', font: {{ size: 11 }} }},
                grid: {{ display: false }}
            }}
        }},
        interaction: {{ mode: 'nearest', axis: 'x' }}
    }}
}});
</script>""")

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ATR (20) 指标 - 创新药企</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f7; color: #1d1d1f; padding: 24px; }}
h1 {{ font-size: 22px; font-weight: 600; margin-bottom: 4px; }}
.subtitle {{ font-size: 13px; color: #888; margin-bottom: 24px; }}
.card {{ background: #fff; border-radius: 12px; border: 0.5px solid rgba(0,0,0,0.1); margin-bottom: 20px; overflow: hidden; }}
.card-header {{ display: flex; justify-content: space-between; align-items: center; padding: 16px 20px 0; flex-wrap: wrap; gap: 8px; }}
.card-title {{ font-size: 15px; font-weight: 500; }}
.card-tags {{ display: flex; gap: 6px; flex-wrap: wrap; }}
.tag {{ font-size: 11px; padding: 2px 8px; border-radius: 4px; background: #f0f0f0; color: #555; }}
.tag.trend-上升 {{ background: #FCEBEB; color: #A32D2D; }}
.tag.trend-下降 {{ background: #E6F1FB; color: #185FA5; }}
.tag.trend-平稳 {{ background: #F1EFE8; color: #5F5E5A; }}
.card-body {{ padding: 16px 20px 20px; }}
.metric-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }}
.metric {{ background: #f8f8fa; border-radius: 8px; padding: 10px 12px; }}
.metric-label {{ font-size: 11px; color: #888; margin-bottom: 2px; }}
.metric-value {{ font-size: 18px; font-weight: 500; }}
.metric-sub {{ font-size: 10px; color: #aaa; margin-top: 2px; }}
.chart-wrap {{ position: relative; width: 100%; height: 280px; }}
@media (max-width: 640px) {{ .metric-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
</style>
</head>
<body>
<h1>ATR(20) 指标计算 — 海龟策略风控参数</h1>
<p class="subtitle">Wilder 平滑法 · 周期=20 · 数据更新至 2026-07-10</p>
{chr(10).join(charts)}
</body>
</html>"""

with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(html)

print(f"ATR 图表已生成: {OUT_HTML}")
