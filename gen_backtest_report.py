#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成全面量化回测可视化报告 HTML。
包含: 汇总指标表, 净值曲线(策略vs基准), 回撤图, 逐标的指标卡片。
"""
import json
import os

BASE_DIR  = r"D:\AI\线上学习"
BT_DIR    = os.path.join(BASE_DIR, "data", "backtest")
OUT_HTML  = os.path.join(BASE_DIR, "backtest_report.html")

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

# 读取汇总
with open(os.path.join(BT_DIR, "backtest_summary.json"), "r", encoding="utf-8") as f:
    summary = json.load(f)

# 读取每个标的净值曲线
all_data = []
for s in summary["stocks"]:
    prefix = NAME_MAP.get((s["name"], s["market"]), "")
    eq_path = os.path.join(BT_DIR, f"{prefix}_equity.json")
    with open(eq_path, "r", encoding="utf-8") as f:
        equity = json.load(f)
    all_data.append({**s, "equity_curve": equity})

# ── 生成汇总表行 ──
def fmt(val, suffix="", color_by_sign=False):
    if val is None:
        return '<span class="na">—</span>'
    s = f"{val:+.2f}{suffix}" if color_by_sign else f"{val:.2f}{suffix}"
    if color_by_sign:
        color = "#ec0000" if val > 0 else ("#00da3c" if val < 0 else "#999")
        return f'<span style="color:{color}">{s}</span>'
    return s

table_rows = ""
for s in all_data:
    pf = s.get("profit_factor")
    wlr = s.get("win_loss_ratio")
    pf_str = f"{pf:.3f}" if pf is not None else "—"
    wlr_str = f"{wlr:.2f}" if wlr is not None else "—"
    
    row = f"""<tr>
        <td class="left">{s['name']}</td>
        <td>{s['market']}</td>
        <td>{fmt(s['strategy_total_return_pct'], '%', True)}</td>
        <td>{fmt(s['bh_total_return_pct'], '%', True)}</td>
        <td>{fmt(s['excess_return_pct'], '%', True)}</td>
        <td>{fmt(s['strategy_annual_return_pct'], '%', True)}</td>
        <td>{s['strategy_max_drawdown_pct']:.2f}%</td>
        <td>{s['strategy_volatility_pct']:.1f}%</td>
        <td>{s['strategy_sharpe']:.2f}</td>
        <td>{s['strategy_sortino']:.2f}</td>
        <td>{s['strategy_calmar']:.2f}</td>
        <td>{s['win_rate_pct']:.0f}%</td>
        <td>{pf_str}</td>
        <td>{wlr_str}</td>
        <td>{fmt(s['expectancy_pct'], '%', True)}</td>
        <td>{s['max_consecutive_wins']}/{s['max_consecutive_losses']}</td>
        <td>{s['holding_ratio_pct']:.0f}%</td>
    </tr>"""
    table_rows += row

# ── 生成逐标的卡片HTML ──
cards_html = ""
for i, s in enumerate(all_data):
    pnl_color = "#ec0000" if s['strategy_total_return_pct'] >= 0 else "#00da3c"
    exc_color = "#ec0000" if s['excess_return_pct'] >= 0 else "#00da3c"
    sharpe_color = "#ec0000" if s['strategy_sharpe'] >= 0 else "#00da3c"
    
    pf = s.get("profit_factor")
    wlr = s.get("win_loss_ratio")
    
    card = f"""
    <div class="stock-card">
        <div class="card-header">
            <div class="card-title">
                <span class="stock-name">{s['name']}</span>
                <span class="stock-market">{s['market']}</span>
                <span class="stock-code">{s['code']}</span>
            </div>
        </div>
        <div class="card-metrics">
            <div class="metric-group">
                <div class="metric"><span class="m-label">策略收益</span><span class="m-val" style="color:{pnl_color}">{s['strategy_total_return_pct']:+.2f}%</span></div>
                <div class="metric"><span class="m-label">基准收益</span><span class="m-val">{s['bh_total_return_pct']:+.2f}%</span></div>
                <div class="metric"><span class="m-label">超额收益</span><span class="m-val" style="color:{exc_color}">{s['excess_return_pct']:+.2f}%</span></div>
                <div class="metric"><span class="m-label">年化收益</span><span class="m-val">{s['strategy_annual_return_pct']:+.2f}%</span></div>
            </div>
            <div class="metric-group">
                <div class="metric"><span class="m-label">最大回撤</span><span class="m-val" style="color:#00da3c">{s['strategy_max_drawdown_pct']:.2f}%</span></div>
                <div class="metric"><span class="m-label">回撤持续</span><span class="m-val">{s['strategy_max_dd_duration']}天</span></div>
                <div class="metric"><span class="m-label">波动率</span><span class="m-val">{s['strategy_volatility_pct']:.1f}%</span></div>
                <div class="metric"><span class="m-label">夏普比率</span><span class="m-val" style="color:{sharpe_color}">{s['strategy_sharpe']:.2f}</span></div>
            </div>
            <div class="metric-group">
                <div class="metric"><span class="m-label">索提诺</span><span class="m-val">{s['strategy_sortino']:.2f}</span></div>
                <div class="metric"><span class="m-label">卡玛比率</span><span class="m-val">{s['strategy_calmar']:.2f}</span></div>
                <div class="metric"><span class="m-label">胜率</span><span class="m-val">{s['win_rate_pct']:.0f}%</span></div>
                <div class="metric"><span class="m-label">利润因子</span><span class="m-val">{f'{pf:.3f}' if pf else '—'}</span></div>
            </div>
            <div class="metric-group">
                <div class="metric"><span class="m-label">平均盈利</span><span class="m-val" style="color:#ec0000">+{s['avg_win_pct']:.2f}%</span></div>
                <div class="metric"><span class="m-label">平均亏损</span><span class="m-val" style="color:#00da3c">{s['avg_loss_pct']:.2f}%</span></div>
                <div class="metric"><span class="m-label">盈亏比</span><span class="m-val">{f'{wlr:.2f}' if wlr else '—'}</span></div>
                <div class="metric"><span class="m-label">期望值</span><span class="m-val">{s['expectancy_pct']:+.2f}%</span></div>
            </div>
            <div class="metric-group">
                <div class="metric"><span class="m-label">最大连胜</span><span class="m-val">{s['max_consecutive_wins']}次</span></div>
                <div class="metric"><span class="m-label">最大连亏</span><span class="m-val">{s['max_consecutive_losses']}次</span></div>
                <div class="metric"><span class="m-label">平均持仓</span><span class="m-val">{s['avg_holding_days']}天</span></div>
                <div class="metric"><span class="m-label">持仓占比</span><span class="m-val">{s['holding_ratio_pct']:.0f}%</span></div>
            </div>
            <div class="metric-group">
                <div class="metric"><span class="m-label">交易次数</span><span class="m-val">{s['total_trades']}笔</span></div>
                <div class="metric"><span class="m-label">盈/亏</span><span class="m-val">{s['win_trades']}/{s['loss_trades']}</span></div>
                <div class="metric"><span class="m-label">日胜率</span><span class="m-val">{s['daily_win_rate_pct']:.1f}%</span></div>
                <div class="metric"><span class="m-label">最终净值</span><span class="m-val">{s['final_strategy_equity']:.0f}</span></div>
            </div>
        </div>
        <div id="eq_chart_{i}" class="eq-chart"></div>
    </div>
    """
    cards_html += card

# ── JS数据 (净值曲线) ──
eq_data_js = []
for s in all_data:
    dates = [d["trade_date"] for d in s["equity_curve"]]
    strat_eq = [d["strategy_equity"] for d in s["equity_curve"]]
    bh_eq = [d["bh_equity"] for d in s["equity_curve"]]
    
    # 计算回撤序列
    peak = strat_eq[0]
    drawdowns = []
    for eq in strat_eq:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak * 100 if peak > 0 else 0
        drawdowns.append(round(dd, 2))
    
    eq_data_js.append({
        "name": s["name"],
        "market": s["market"],
        "dates": dates,
        "strategy": strat_eq,
        "bh": bh_eq,
        "drawdown": drawdowns,
    })

js_data = json.dumps(eq_data_js, ensure_ascii=False)

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MA(5)/MA(15) 交叉策略 — 全面量化回测报告</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,"Microsoft YaHei","Segoe UI",sans-serif; background:#f5f5f5; color:#333; padding:20px; }}
.header {{ text-align:center; padding:30px 0 24px; background:#fff; border-radius:12px; margin-bottom:20px; box-shadow:0 2px 8px rgba(0,0,0,0.06); }}
.header h1 {{ font-size:24px; color:#1a1a1a; margin-bottom:8px; }}
.header .sub {{ font-size:13px; color:#888; margin-bottom:6px; }}
.header .tags {{ display:flex; justify-content:center; gap:8px; margin-top:10px; flex-wrap:wrap; }}
.tag {{ display:inline-block; background:#f0f5ff; color:#1890ff; padding:3px 12px; border-radius:4px; font-size:12px; }}

.summary-cards {{ display:grid; grid-template-columns:repeat(6,1fr); gap:12px; margin-bottom:20px; }}
.s-card {{ background:#fff; border-radius:10px; padding:16px; text-align:center; box-shadow:0 1px 4px rgba(0,0,0,0.05); }}
.s-card .label {{ font-size:11px; color:#999; margin-bottom:6px; }}
.s-card .value {{ font-size:20px; font-weight:700; }}

.section-title {{ font-size:17px; font-weight:600; margin:24px 0 12px; padding-left:12px; border-left:4px solid #1890ff; }}

.table-wrap {{ background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.06); margin-bottom:20px; overflow-x:auto; }}
table {{ width:100%; border-collapse:collapse; font-size:12px; }}
th {{ background:#fafafa; padding:10px 8px; text-align:center; color:#666; font-weight:600; white-space:nowrap; border-bottom:2px solid #eee; }}
td {{ padding:8px; text-align:center; border-bottom:1px solid #f5f5f5; white-space:nowrap; }}
td.left {{ text-align:left; font-weight:600; }}
tr:hover {{ background:#fafafa; }}
.na {{ color:#ccc; }}

.stock-card {{ background:#fff; border-radius:12px; margin-bottom:20px; box-shadow:0 2px 8px rgba(0,0,0,0.06); overflow:hidden; }}
.card-header {{ padding:16px 20px; border-bottom:1px solid #f0f0f0; }}
.card-title {{ display:flex; align-items:center; gap:10px; }}
.stock-name {{ font-size:17px; font-weight:600; }}
.stock-market {{ font-size:12px; background:#f0f0f0; padding:2px 8px; border-radius:4px; color:#666; }}
.stock-code {{ font-size:12px; color:#999; font-family:monospace; }}
.card-metrics {{ display:grid; grid-template-columns:repeat(6,1fr); gap:8px; padding:16px 20px; }}
.metric-group {{ display:flex; flex-direction:column; gap:8px; }}
.metric {{ display:flex; flex-direction:column; gap:2px; padding:6px 8px; background:#fafafa; border-radius:6px; }}
.m-label {{ font-size:10px; color:#999; }}
.m-val {{ font-size:14px; font-weight:600; }}
.eq-chart {{ width:100%; height:360px; }}

.footer {{ text-align:center; padding:20px; color:#aaa; font-size:12px; }}
</style>
</head>
<body>

<div class="header">
    <h1>MA(5)/MA(15) 交叉策略 — 全面量化回测报告</h1>
    <div class="sub">回测区间: {summary['meta']['period']} | 初始资金: {summary['meta']['initial_capital']:,.0f} | 无风险利率: {summary['meta']['risk_free_rate']*100:.1f}%</div>
    <div class="sub">策略: {summary['meta']['strategy']}</div>
    <div class="tags">
        <span class="tag">8个标的</span>
        <span class="tag">日线回测</span>
        <span class="tag">含基准对比</span>
        <span class="tag">15项量化指标</span>
    </div>
</div>

<div class="summary-cards">
    <div class="s-card"><div class="label">策略平均收益</div><div class="value" style="color:#ec0000">+{sum(s['strategy_total_return_pct'] for s in all_data)/len(all_data):.1f}%</div></div>
    <div class="s-card"><div class="label">基准平均收益</div><div class="value">+{sum(s['bh_total_return_pct'] for s in all_data)/len(all_data):.1f}%</div></div>
    <div class="s-card"><div class="label">跑赢基准</div><div class="value" style="color:#ec0000">{sum(1 for s in all_data if s['excess_return_pct']>0)}/8</div></div>
    <div class="s-card"><div class="label">平均夏普</div><div class="value">{sum(s['strategy_sharpe'] for s in all_data)/len(all_data):.2f}</div></div>
    <div class="s-card"><div class="label">平均最大回撤</div><div class="value" style="color:#00da3c">{sum(s['strategy_max_drawdown_pct'] for s in all_data)/len(all_data):.1f}%</div></div>
    <div class="s-card"><div class="label">盈利标的</div><div class="value" style="color:#ec0000">{sum(1 for s in all_data if s['strategy_total_return_pct']>0)}/8</div></div>
</div>

<div class="section-title">量化指标汇总表</div>
<div class="table-wrap">
<table>
<thead>
<tr>
    <th>标的</th><th>市场</th>
    <th>策略收益</th><th>基准收益</th><th>超额收益</th><th>年化收益</th>
    <th>最大回撤</th><th>波动率</th>
    <th>夏普</th><th>索提诺</th><th>卡玛</th>
    <th>胜率</th><th>利润因子</th><th>盈亏比</th><th>期望值</th>
    <th>连胜/连亏</th><th>持仓占比</th>
</tr>
</thead>
<tbody>
{table_rows}
</tbody>
</table>
</div>

<div class="section-title">逐标的净值曲线与详细指标</div>
{cards_html}

<div class="footer">
    Generated by calc_backtest.py + gen_backtest_report.py | 量化回测仅供参考，不构成投资建议
</div>

<script>
var eqData = {js_data};

eqData.forEach(function(item, idx) {{
    var chartDom = document.getElementById('eq_chart_' + idx);
    var myChart = echarts.init(chartDom);
    
    var option = {{
        backgroundColor: '#fff',
        title: {{
            text: item.name + '(' + item.market + ') — 净值曲线 & 回撤',
            left: 'center',
            textStyle: {{ fontSize: 13, color: '#666' }}
        }},
        tooltip: {{
            trigger: 'axis',
            axisPointer: {{ type: 'cross' }},
            formatter: function(params) {{
                var date = params[0].axisValue;
                var html = '<div style="font-size:12px;line-height:1.6"><b>' + date + '</b>';
                params.forEach(function(p) {{
                    var val = typeof p.data === 'number' ? p.data.toFixed(2) : p.data;
                    var unit = p.seriesName === '回撤' ? '%' : '';
                    html += '<br/><span style="color:' + p.color + '">●</span> ' + p.seriesName + ': ' + val + unit;
                }});
                html += '</div>';
                return html;
            }}
        }},
        legend: {{
            data: ['策略净值', '买入持有', '回撤'],
            top: 25,
            textStyle: {{ fontSize: 11 }}
        }},
        grid: [
            {{ left: '7%', right: '4%', top: '12%', height: '52%' }},
            {{ left: '7%', right: '4%', top: '70%', height: '20%' }}
        ],
        xAxis: [
            {{
                type: 'category', data: item.dates,
                gridIndex: 0, boundaryGap: false,
                axisLabel: {{ show: false }},
                axisLine: {{ lineStyle: {{ color: '#ddd' }} }}
            }},
            {{
                type: 'category', data: item.dates,
                gridIndex: 1, boundaryGap: false,
                axisLabel: {{ color: '#999', fontSize: 10, formatter: function(v) {{ return v.substring(5); }} }},
                axisLine: {{ lineStyle: {{ color: '#ddd' }} }}
            }}
        ],
        yAxis: [
            {{
                type: 'value', gridIndex: 0, scale: true,
                axisLabel: {{ color: '#999', fontSize: 10 }},
                splitLine: {{ lineStyle: {{ color: '#f5f5f5' }} }}
            }},
            {{
                type: 'value', gridIndex: 1, max: 0,
                axisLabel: {{ color: '#999', fontSize: 10, formatter: '{{value}}%' }},
                splitLine: {{ lineStyle: {{ color: '#f5f5f5' }} }}
            }}
        ],
        dataZoom: [
            {{ type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 }},
            {{ show: true, type: 'slider', xAxisIndex: [0, 1], bottom: '2%', height: 16, start: 0, end: 100,
               borderColor: '#eee', fillerColor: 'rgba(24,144,255,0.1)', handleStyle: {{ color: '#1890ff' }} }}
        ],
        series: [
            {{
                name: '策略净值', type: 'line', xAxisIndex: 0, yAxisIndex: 0,
                data: item.strategy, symbol: 'none',
                lineStyle: {{ color: '#ec0000', width: 2 }},
                areaStyle: {{ color: 'rgba(236,0,0,0.05)' }}
            }},
            {{
                name: '买入持有', type: 'line', xAxisIndex: 0, yAxisIndex: 0,
                data: item.bh, symbol: 'none',
                lineStyle: {{ color: '#2b6cb0', width: 1.5, type: 'dashed' }}
            }},
            {{
                name: '回撤', type: 'line', xAxisIndex: 1, yAxisIndex: 1,
                data: item.drawdown, symbol: 'none',
                lineStyle: {{ color: '#00da3c', width: 1 }},
                areaStyle: {{ color: 'rgba(0,218,60,0.1)' }}
            }}
        ]
    }};
    
    myChart.setOption(option);
    window.addEventListener('resize', function() {{ myChart.resize(); }});
}});
</script>

</body>
</html>
"""

with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(html)

print(f"回测报告已生成: {OUT_HTML}")
