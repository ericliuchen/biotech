import json
from pathlib import Path

CHANNELS_DIR = Path("D:/AI/线上学习/data/channels")
OUT_HTML = Path("D:/AI/线上学习/donchian_channels.html")

summary_file = CHANNELS_DIR / "_channel_summary.json"
with open(summary_file, "r", encoding="utf-8") as f:
    summary = json.load(f)

stocks = summary["stocks"]

# Create one chart section per stock
chart_sections = []
chart_configs = []

for idx, s in enumerate(stocks):
    ch_file = CHANNELS_DIR / s["file"]
    with open(ch_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Only take valid records (channel data available)
    valid = [d for d in data if d["channel_upper"] is not None]
    # Take last 120 records (about 6 months of daily data)
    plot_data = valid[-120:] if len(valid) > 120 else valid

    dates = [d["trade_date"] for d in plot_data]
    closes = [d["close"] for d in plot_data]
    uppers = [d["channel_upper"] for d in plot_data]
    lowers = [d["channel_lower"] for d in plot_data]
    middles = [d["channel_middle"] for d in plot_data]

    label = f"{s['company']} ({s['code']} {s['market']})"
    chart_id = f"chart_{idx}"

    chart_sections.append(f"""
<div class="chart-card">
  <div class="chart-header">
    <div class="chart-title">{label}</div>
    <div class="chart-info">
      <span>上轨: <b>{s['channel_upper']}</b></span>
      <span>中轨: <b>{s['channel_middle']}</b></span>
      <span>下轨: <b>{s['channel_lower']}</b></span>
      <span>通道宽: <b>{s['channel_width']}</b></span>
      <span>价格位置: <b>{s['price_position_pct']}%</b> ({s['currency']})</span>
    </div>
  </div>
  <div class="chart-wrapper">
    <canvas id="{chart_id}" role="img" aria-label="Price chart with Donchian channel for {label}"></canvas>
  </div>
</div>""")

    chart_configs.append(f"""
    const ctx{idx} = document.getElementById('{chart_id}').getContext('2d');
    new Chart(ctx{idx}, {{
        type: 'line',
        data: {{
            labels: {json.dumps(dates)},
            datasets: [
                {{
                    label: '上轨 (20日高)',
                    data: {json.dumps(uppers)},
                    borderColor: '#378ADD',
                    backgroundColor: 'rgba(55,138,221,0.05)',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    fill: false,
                    tension: 0.2
                }},
                {{
                    label: '中轨',
                    data: {json.dumps(middles)},
                    borderColor: '#888780',
                    borderWidth: 0.5,
                    borderDash: [4, 4],
                    pointRadius: 0,
                    fill: false,
                    tension: 0.2
                }},
                {{
                    label: '下轨 (20日低)',
                    data: {json.dumps(lowers)},
                    borderColor: '#378ADD',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    fill: false,
                    tension: 0.2
                }},
                {{
                    label: '收盘价',
                    data: {json.dumps(closes)},
                    borderColor: '#D85A30',
                    backgroundColor: 'rgba(216,90,48,0.1)',
                    borderWidth: 2,
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
                legend: {{ display: false }},
                tooltip: {{ mode: 'index', intersect: false }}
            }},
            scales: {{
                x: {{
                    ticks: {{ autoSkip: true, maxTicksLimit: 10, maxRotation: 0 }},
                    grid: {{ display: false }}
                }},
                y: {{
                    grid: {{ color: 'rgba(0,0,0,0.06)' }}
                }}
            }},
            interaction: {{ mode: 'nearest', axis: 'x' }}
        }}
    }});""")

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>20日唐奇安通道 - 创新药企</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f7; color: #1d1d1f; padding: 24px; }}
h1 {{ font-size: 22px; font-weight: 600; margin-bottom: 4px; }}
.subtitle {{ font-size: 13px; color: #888; margin-bottom: 24px; }}
.chart-card {{ background: #fff; border-radius: 12px; border: 0.5px solid rgba(0,0,0,0.1); padding: 20px; margin-bottom: 20px; }}
.chart-header {{ display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; margin-bottom: 12px; gap: 8px; }}
.chart-title {{ font-size: 15px; font-weight: 500; }}
.chart-info {{ display: flex; flex-wrap: wrap; gap: 12px; font-size: 12px; color: #555; }}
.chart-info b {{ font-weight: 500; }}
.chart-wrapper {{ position: relative; width: 100%; height: 320px; }}
.legend {{ display: flex; flex-wrap: wrap; gap: 16px; font-size: 12px; color: #666; margin-bottom: 16px; padding: 8px 0; border-bottom: 0.5px solid rgba(0,0,0,0.08); }}
.legend span {{ display: flex; align-items: center; gap: 4px; }}
.legend-dot {{ width: 10px; height: 10px; border-radius: 2px; display: inline-block; }}
.summary-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 12px; margin-bottom: 24px; }}
.summary-card {{ background: #fff; border-radius: 10px; border: 0.5px solid rgba(0,0,0,0.08); padding: 14px 16px; }}
.summary-card .name {{ font-size: 13px; font-weight: 500; margin-bottom: 6px; }}
.summary-card .row {{ display: flex; justify-content: space-between; font-size: 12px; color: #555; padding: 2px 0; }}
.summary-card .pos-bar {{ height: 6px; border-radius: 3px; background: #eee; margin-top: 6px; overflow: hidden; }}
.summary-card .pos-fill {{ height: 100%; border-radius: 3px; }}
</style>
</head>
<body>

<h1>创新药企 20 日唐奇安通道</h1>
<p class="subtitle">基于近半年日线数据 · 上轨 = 20日最高价 · 下轨 = 20日最低价 · 更新至 2026-07-10</p>

<div style="display: flex; flex-wrap: wrap; gap: 16px; font-size: 12px; color: #666; margin-bottom: 16px;">
  <span style="display: flex; align-items: center; gap: 4px;"><span class="legend-dot" style="background:#378ADD;"></span>上轨 / 下轨</span>
  <span style="display: flex; align-items: center; gap: 4px;"><span class="legend-dot" style="background:#888780;"></span>中轨</span>
  <span style="display: flex; align-items: center; gap: 4px;"><span class="legend-dot" style="background:#D85A30;"></span>收盘价</span>
  <span style="display: flex; align-items: center; gap: 4px;"><span class="legend-dot" style="background:#34C759;"></span>价格在通道中的位置</span>
</div>

<div class="summary-grid">
{chr(10).join(
    f'''<div class="summary-card">
    <div class="name">{s['company']} ({s['code']} {s['market']})</div>
    <div class="row"><span>最新价</span><span><b>{s['latest_close']:.2f}</b> {s['currency']}</span></div>
    <div class="row"><span>上轨 / 下轨</span><span>{s['channel_upper']:.2f} / {s['channel_lower']:.2f}</span></div>
    <div class="row"><span>通道宽度</span><span>{s['channel_width']:.2f}</span></div>
    <div class="row"><span>价格位置</span><span><b>{s['price_position_pct']:.1f}%</b> (距下轨)</span></div>
    <div class="pos-bar"><div class="pos-fill" style="width:{s['price_position_pct']:.1f}%;background:{'#34C759' if s['price_position_pct']>60 else '#FF9500' if s['price_position_pct']>40 else '#FF3B30'};"></div></div>
  </div>'''
    for s in stocks
)}
</div>

{chr(10).join(chart_sections)}

<script>
{chr(10).join(chart_configs)}
</script>

</body>
</html>"""

with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(html)

print(f"HTML 图表已生成: {OUT_HTML}")
