#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成8个标的的股价+均线+交易信号可视化HTML页面。
使用 ECharts 绘制K线图+MA均线+买卖信号标记。
"""
import json
import os

BASE_DIR = r"D:\AI\线上学习"
SIG_DIR  = os.path.join(BASE_DIR, "data", "signals")
OUT_HTML = os.path.join(BASE_DIR, "trade_signals_chart.html")

# 读取汇总
with open(os.path.join(SIG_DIR, "signal_summary.json"), "r", encoding="utf-8") as f:
    summary = json.load(f)

STOCKS = summary["stocks"]

# 读取每个标的的信号数据
all_data = []
for s in STOCKS:
    sig_file = s["name"] + "(" + s["market"] + ")_" + s["code"]
    # 从汇总中找对应的 signals 文件名
    # 文件名模式: {short}_{mkt}_{code}_signals.json
    # 需要映射
    name_map = {
        ("恒瑞医药", "A股"): "hengrui_A_600276",
        ("恒瑞医药", "港股"): "hengrui_HK_01276",
        ("百济神州", "美股"): "beigene_US_ONC",
        ("百济神州", "港股"): "beigene_HK_06160",
        ("百济神州", "A股"): "beigene_A_688235",
        ("信达生物", "港股"): "innovent_HK_01801",
        ("君实生物", "港股"): "junshi_HK_01877",
        ("君实生物", "A股"): "junshi_A_688180",
    }
    file_prefix = name_map.get((s["name"], s["market"]), "")
    sig_path = os.path.join(SIG_DIR, f"{file_prefix}_signals.json")
    
    with open(sig_path, "r", encoding="utf-8") as f:
        signals = json.load(f)
    
    all_data.append({
        "name": s["name"],
        "market": s["market"],
        "code": s["code"],
        "currency": s["currency"],
        "perf": s,
        "signals": signals,
    })

# 为 ECharts 准备数据
def prepare_chart_data(stock_data):
    signals = stock_data["signals"]
    dates = []
    ohlc = []      # [open, close, low, high] (ECharts candlestick 顺序)
    ma5_data = []
    ma15_data = []
    buy_points = []   # {coord: [date, price], value, itemStyle}
    sell_points = []
    buy_labels = []
    sell_labels = []
    
    for i, rec in enumerate(signals):
        dates.append(rec["trade_date"])
        # ECharts K线: [open, close, low, high]
        ohlc.append([rec["open"], rec["close"], rec["low"], rec["high"]])
        
        ma5 = rec.get("ma5")
        ma15 = rec.get("ma15")
        ma5_data.append(ma5 if ma5 is not None else None)
        ma15_data.append(ma15 if ma15 is not None else None)
        
        sig = rec.get("trade_signal", "")
        if sig == "BUY":
            buy_points.append({
                "coord": [i, rec["close"]],
                "itemStyle": {"color": "#ec0000"},
            })
            buy_labels.append({
                "coord": [i, rec["low"] * 0.985],
                "value": "买",
            })
        elif sig == "SELL":
            sell_points.append({
                "coord": [i, rec["close"]],
                "itemStyle": {"color": "#00da3c"},
            })
            sell_labels.append({
                "coord": [i, rec["high"] * 1.015],
                "value": "卖",
            })
    
    return {
        "dates": dates,
        "ohlc": ohlc,
        "ma5": ma5_data,
        "ma15": ma15_data,
        "buy_points": buy_points,
        "sell_points": sell_points,
        "buy_labels": buy_labels,
        "sell_labels": sell_labels,
    }


# 生成所有图表数据
charts_data = []
for sd in all_data:
    cd = prepare_chart_data(sd)
    charts_data.append({
        "name": sd["name"],
        "market": sd["market"],
        "code": sd["code"],
        "currency": sd["currency"],
        "perf": sd["perf"],
        "chart": cd,
    })

# 生成 HTML
# 每个图表一个 div，使用 ECharts 实例化

stock_cards_html = ""
for i, cd in enumerate(charts_data):
    perf = cd["perf"]
    pnl_color = "#ec0000" if perf["total_pnl"] >= 0 else "#00da3c"
    win_color = "#ec0000" if perf["win_rate_pct"] >= 50 else "#00da3c"
    unreal_color = "#ec0000" if (perf["unrealized_pnl_pct"] or 0) >= 0 else "#00da3c"
    
    card = f"""
    <div class="stock-card">
        <div class="stock-header">
            <div class="stock-title">
                <span class="stock-name">{cd['name']}</span>
                <span class="stock-market">{cd['market']}</span>
                <span class="stock-code">{cd['code']}</span>
            </div>
            <div class="stock-perf">
                <div class="perf-item"><span class="perf-label">交易次数</span><span class="perf-val">{perf['total_trades']}</span></div>
                <div class="perf-item"><span class="perf-label">胜率</span><span class="perf-val" style="color:{win_color}">{perf['win_rate_pct']}%</span></div>
                <div class="perf-item"><span class="perf-label">已实现盈亏</span><span class="perf-val" style="color:{pnl_color}">{perf['total_pnl']} {cd['currency']}</span></div>
                <div class="perf-item"><span class="perf-label">浮动盈亏</span><span class="perf-val" style="color:{unreal_color}">{perf['unrealized_pnl_pct']}%</span></div>
                <div class="perf-item"><span class="perf-label">当前状态</span><span class="perf-val">{perf['current_position']}</span></div>
            </div>
        </div>
        <div id="chart_{i}" class="chart-container"></div>
    </div>
    """
    stock_cards_html += card

# 构建 JS 数据
js_data = json.dumps(charts_data, ensure_ascii=False)

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>医药股 MA(5)/MA(15) 交叉策略 — 交易信号可视化</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: -apple-system, "Microsoft YaHei", "Segoe UI", sans-serif;
        background: #f5f5f5;
        color: #333;
        padding: 20px;
    }}
    .header {{
        text-align: center;
        padding: 24px 0 20px;
        background: #fff;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }}
    .header h1 {{
        font-size: 22px;
        color: #1a1a1a;
        margin-bottom: 8px;
    }}
    .header .subtitle {{
        font-size: 13px;
        color: #888;
    }}
    .header .strategy-tag {{
        display: inline-block;
        background: #e8f4ff;
        color: #1890ff;
        padding: 3px 12px;
        border-radius: 4px;
        font-size: 12px;
        margin-top: 8px;
    }}
    .legend-bar {{
        display: flex;
        justify-content: center;
        gap: 24px;
        padding: 12px 0;
        background: #fff;
        border-radius: 8px;
        margin-bottom: 16px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        flex-wrap: wrap;
    }}
    .legend-item {{
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
        color: #666;
    }}
    .legend-dot {{
        width: 12px;
        height: 12px;
        border-radius: 50%;
        flex-shrink: 0;
    }}
    .legend-line {{
        width: 20px;
        height: 3px;
        border-radius: 2px;
        flex-shrink: 0;
    }}
    .stock-card {{
        background: #fff;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        overflow: hidden;
    }}
    .stock-header {{
        padding: 16px 20px 12px;
        border-bottom: 1px solid #f0f0f0;
    }}
    .stock-title {{
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 10px;
    }}
    .stock-name {{
        font-size: 17px;
        font-weight: 600;
        color: #1a1a1a;
    }}
    .stock-market {{
        font-size: 12px;
        background: #f0f0f0;
        padding: 2px 8px;
        border-radius: 4px;
        color: #666;
    }}
    .stock-code {{
        font-size: 12px;
        color: #999;
        font-family: monospace;
    }}
    .stock-perf {{
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
    }}
    .perf-item {{
        display: flex;
        flex-direction: column;
        gap: 2px;
    }}
    .perf-label {{
        font-size: 11px;
        color: #999;
    }}
    .perf-val {{
        font-size: 15px;
        font-weight: 600;
        color: #333;
    }}
    .chart-container {{
        width: 100%;
        height: 420px;
    }}
    .footer {{
        text-align: center;
        padding: 16px;
        color: #aaa;
        font-size: 12px;
    }}
    .summary-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        padding: 20px;
        background: #fff;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }}
    .summary-cell {{
        text-align: center;
        padding: 12px;
        border-radius: 8px;
        background: #fafafa;
    }}
    .summary-cell .label {{
        font-size: 11px;
        color: #999;
        margin-bottom: 4px;
    }}
    .summary-cell .value {{
        font-size: 18px;
        font-weight: 700;
    }}
</style>
</head>
<body>

<div class="header">
    <h1>医药股 MA(5)/MA(15) 交叉策略 — 交易信号可视化</h1>
    <div class="subtitle">数据范围: {summary['meta']['start_date']} ~ {summary['meta']['end_date']} | 数据源: {summary['meta']['data_source']}</div>
    <div class="strategy-tag">{summary['meta']['strategy']}</div>
</div>

<div class="summary-grid">
    <div class="summary-cell">
        <div class="label">标的数量</div>
        <div class="value" style="color:#1890ff">{len(charts_data)}</div>
    </div>
    <div class="summary-cell">
        <div class="label">总交易次数</div>
        <div class="value">{sum(c['perf']['total_trades'] for c in charts_data)}</div>
    </div>
    <div class="summary-cell">
        <div class="label">盈利标的</div>
        <div class="value" style="color:#ec0000">{sum(1 for c in charts_data if c['perf']['total_pnl'] >= 0)}</div>
    </div>
    <div class="summary-cell">
        <div class="label">持仓标的</div>
        <div class="value">{sum(1 for c in charts_data if c['perf']['current_position'] == '持仓中')}</div>
    </div>
</div>

<div class="legend-bar">
    <div class="legend-item"><div class="legend-dot" style="background:#ec0000"></div> 阳线(涨)</div>
    <div class="legend-item"><div class="legend-dot" style="background:#00da3c"></div> 阴线(跌)</div>
    <div class="legend-item"><div class="legend-line" style="background:#ff6b35"></div> MA5(短均线)</div>
    <div class="legend-item"><div class="legend-line" style="background:#2b6cb0"></div> MA15(长均线)</div>
    <div class="legend-item"><div class="legend-dot" style="background:#ec0000;border:2px solid #fff;box-shadow:0 0 0 1px #ec0000"></div> 买入信号</div>
    <div class="legend-item"><div class="legend-dot" style="background:#00da3c;border:2px solid #fff;box-shadow:0 0 0 1px #00da3c"></div> 卖出信号</div>
</div>

{stock_cards_html}

<div class="footer">
    Generated by calc_signals.py + gen_chart.py | 策略仅供参考，不构成投资建议
</div>

<script>
var allData = {js_data};

allData.forEach(function(item, idx) {{
    var chartDom = document.getElementById('chart_' + idx);
    var myChart = echarts.init(chartDom);
    var cd = item.chart;
    var perf = item.perf;
    
    var option = {{
        backgroundColor: '#fff',
        tooltip: {{
            trigger: 'axis',
            axisPointer: {{
                type: 'cross',
                crossStyle: {{ color: '#999' }}
            }},
            formatter: function(params) {{
                var date = params[0].axisValue;
                var html = '<div style="font-size:12px;line-height:1.8">';
                html += '<b>' + date + '</b><br/>';
                params.forEach(function(p) {{
                    if (p.seriesType === 'candlestick') {{
                        var d = p.data;
                        var color = d[1] >= d[0] ? '#ec0000' : '#00da3c';
                        html += '<span style="color:' + color + '">●</span> 开:' + d[0] + ' 收:' + d[1] + '<br/>';
                        html += '<span style="color:#999">●</span> 低:' + d[2] + ' 高:' + d[3] + '<br/>';
                    }} else if (p.seriesType === 'line' && p.data != null) {{
                        html += '<span style="color:' + p.color + '">●</span> ' + p.seriesName + ': ' + p.data + '<br/>';
                    }}
                }});
                html += '</div>';
                return html;
            }}
        }},
        axisPointer: {{
            link: {{xAxisIndex: 'all'}}
        }},
        grid: {{
            left: '8%',
            right: '4%',
            top: '8%',
            bottom: '15%'
        }},
        xAxis: {{
            type: 'category',
            data: cd.dates,
            boundaryGap: true,
            axisLine: {{ lineStyle: {{ color: '#ddd' }} }},
            axisLabel: {{
                color: '#999',
                fontSize: 11,
                formatter: function(val) {{
                    return val.substring(5);  // MM-DD
                }}
            }},
            splitLine: {{ show: false }}
        }},
        yAxis: {{
            scale: true,
            splitNumber: 6,
            axisLine: {{ lineStyle: {{ color: '#ddd' }} }},
            axisLabel: {{
                color: '#999',
                fontSize: 11,
                formatter: function(val) {{
                    return val.toFixed(2);
                }}
            }},
            splitLine: {{ lineStyle: {{ color: '#f5f5f5' }} }}
        }},
        dataZoom: [
            {{
                type: 'inside',
                start: 0,
                end: 100
            }},
            {{
                show: true,
                type: 'slider',
                bottom: '3%',
                start: 0,
                end: 100,
                height: 20,
                borderColor: '#eee',
                fillerColor: 'rgba(24,144,255,0.1)',
                handleStyle: {{ color: '#1890ff' }}
            }}
        ],
        series: [
            {{
                name: 'K线',
                type: 'candlestick',
                data: cd.ohlc,
                itemStyle: {{
                    color: '#ec0000',        // 阳线(涨) 红色
                    color0: '#00da3c',       // 阴线(跌) 绿色
                    borderColor: '#ec0000',
                    borderColor0: '#00da3c'
                }},
                markPoint: {{
                    symbol: 'triangle',
                    symbolSize: 12,
                    data: (function() {{
                        var pts = [];
                        // 买入信号: 红色向上箭头
                        cd.buy_points.forEach(function(bp) {{
                            pts.push({{
                                coord: bp.coord,
                                itemStyle: {{ color: '#ec0000' }},
                                symbolRotate: 0,
                                symbolOffset: [0, 12],
                                label: {{
                                    show: true,
                                    formatter: '买',
                                    color: '#fff',
                                    fontSize: 9,
                                    offset: [0, 12]
                                }}
                            }});
                        }});
                        // 卖出信号: 绿色向下箭头
                        cd.sell_points.forEach(function(sp) {{
                            pts.push({{
                                coord: sp.coord,
                                itemStyle: {{ color: '#00da3c' }},
                                symbolRotate: 180,
                                symbolOffset: [0, -12],
                                label: {{
                                    show: true,
                                    formatter: '卖',
                                    color: '#fff',
                                    fontSize: 9,
                                    offset: [0, -12]
                                }}
                            }});
                        }});
                        return pts;
                    }})()
                }}
            }},
            {{
                name: 'MA5',
                type: 'line',
                data: cd.ma5,
                smooth: true,
                symbol: 'none',
                lineStyle: {{
                    color: '#ff6b35',
                    width: 1.5
                }},
                z: 5
            }},
            {{
                name: 'MA15',
                type: 'line',
                data: cd.ma15,
                smooth: true,
                symbol: 'none',
                lineStyle: {{
                    color: '#2b6cb0',
                    width: 1.5
                }},
                z: 5
            }}
        ]
    }};
    
    myChart.setOption(option);
    
    // 响应窗口大小变化
    window.addEventListener('resize', function() {{
        myChart.resize();
    }});
}});
</script>

</body>
</html>
"""

with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(html)

print(f"HTML 可视化页面已生成: {OUT_HTML}")
print(f"包含 {len(charts_data)} 个标的图表")
