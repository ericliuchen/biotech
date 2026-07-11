# 使用Python生成完整的HTML，将数据内嵌，并增加ATR图表
import json

# 读取数据
with open(r"D:\AI\线上学习\hengrui_indicators_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

data_json = json.dumps(data, ensure_ascii=False)

html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>恒瑞医药(600276) 技术指标分析</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, "Microsoft YaHei", "PingFang SC", sans-serif;
    background: #f5f6fa; color: #333; padding: 16px;
}}
.container {{ max-width: 1300px; margin: 0 auto; }}
h1 {{ text-align: center; font-size: 22px; font-weight: 600; margin-bottom: 4px; }}
.subtitle {{ text-align: center; font-size: 13px; color: #888; margin-bottom: 10px; }}
.chart-box {{ background: #fff; border-radius: 10px; padding: 12px; margin-bottom: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
.chart-box h3 {{ font-size: 14px; font-weight: 600; margin-bottom: 6px; color: #555; padding-left: 6px; border-left: 3px solid #1a73e8; }}
#main-chart {{ width: 100%; height: 460px; }}
#bb-chart  {{ width: 100%; height: 180px; }}
#macd-chart {{ width: 100%; height: 170px; }}
#rsi-chart {{ width: 100%; height: 150px; }}
#atr-chart {{ width: 100%; height: 140px; }}
#rs-chart  {{ width: 100%; height: 150px; }}
</style>
</head>
<body>
<div class="container">
    <h1>恒瑞医药 (600276.SH) 技术指标分析</h1>
    <p class="subtitle">数据区间：2025-07-04 ~ 2026-07-03 · RSI(14) · MACD(12,26,9) · 布林带(20,2) · ATR(14) · RS(恒瑞/中证医药)</p>

    <div class="chart-box"><h3>📈 K线 &amp; 成交量</h3><div id="main-chart"></div></div>
    <div class="chart-box"><h3>📊 布林带 (Bollinger Bands, 20, 2)</h3><div id="bb-chart"></div></div>
    <div class="chart-box"><h3>📉 MACD (12, 26, 9)</h3><div id="macd-chart"></div></div>
    <div class="chart-box"><h3>📊 RSI (14)</h3><div id="rsi-chart"></div></div>
    <div class="chart-box"><h3>📊 ATR (14) - 平均真实波幅</h3><div id="atr-chart"></div></div>
    <div class="chart-box"><h3>📊 RS - 相对强度 (恒瑞 / 中证医药)</h3><div id="rs-chart"></div></div>
</div>

<script>
var DATA = {data_json};

// ─── 颜色 ───
var UP = '#ef232a', DN = '#14b143';

function makeCloses(i) {{ return i === 0 ? true : DATA[i].close >= DATA[i].open; }}

var dates = DATA.map(function(d){{return d.date;}});
var closes = DATA.map(function(d){{return d.close;}});
var vols = DATA.map(function(d){{return d.vol;}});

// 布林带填充
function fill(arr) {{ var r=[],last=null; for(var i=0;i<arr.length;i++){{ if(arr[i]!==null)last=arr[i]; r.push(last); }} return r; }}
var bbUpper = fill(DATA.map(function(d){{return d.bb_upper;}}));
var bbMid   = fill(DATA.map(function(d){{return d.bb_mid;}}));
var bbLower = fill(DATA.map(function(d){{return d.bb_lower;}}));

// 通用tooltip
function tooltipHtml(i) {{
    var d = DATA[i];
    var html = '<strong>' + d.date + '</strong><br/>';
    html += '开: ' + d.open.toFixed(2) + ' 收: <strong>' + d.close.toFixed(2) + '</strong> 高: ' + d.high.toFixed(2) + ' 低: ' + d.low.toFixed(2) + '<br/>';
    html += '量: ' + (d.vol/10000).toFixed(2) + '万手';
    if(d.rsi !== null) html += '<br/>RSI: ' + d.rsi.toFixed(2);
    if(d.macd !== null) html += '<br/>MACD: ' + d.macd.toFixed(4) + ' / 信号: ' + d.signal.toFixed(4) + ' / 柱: ' + d.hist.toFixed(4);
    if(d.atr !== null) html += '<br/>ATR: ' + d.atr.toFixed(4);
    if(d.bb_upper !== null) html += '<br/>布林上: ' + d.bb_upper.toFixed(2) + ' 中: ' + d.bb_mid.toFixed(2) + ' 下: ' + d.bb_lower.toFixed(2);
    if(d.rs !== null) html += '<br/>RS: ' + d.rs.toFixed(6) + ' / RS_MA20: ' + (d.rs_ma20 !== null ? d.rs_ma20.toFixed(6) : '-');
    if(d.idx_close !== null) html += '<br/>中证医药: ' + d.idx_close.toFixed(2);
    return html;
}}

// ── 1. K线 ──
var main = echarts.init(document.getElementById('main-chart'));
main.setOption({{
    animation:false,
    tooltip:{{trigger:'axis', axisPointer:{{type:'cross'}}, backgroundColor:'rgba(255,255,255,0.95)', borderColor:'#ccc', borderWidth:1, textStyle:{{color:'#333',fontSize:12}}, formatter:function(p){{return tooltipHtml(p[0].dataIndex);}} }},
    grid:[ {{left:'3%',right:'3%',top:8,height:'55%'}}, {{left:'3%',right:'3%',top:'68%',height:'18%'}} ],
    xAxis:[
        {{type:'category',data:dates,axisLine:{{onZero:false}},axisTick:{{show:false}},splitLine:{{show:false}},axisLabel:{{show:false}},gridIndex:0}},
        {{type:'category',data:dates,axisLine:{{onZero:false}},axisTick:{{show:false}},splitLine:{{show:true,lineStyle:{{type:'dashed',color:'#e0e0e0'}}}},axisLabel:{{rotate:45,fontSize:10,interval:25}},gridIndex:1}}
    ],
    yAxis:[
        {{scale:true,gridIndex:0,splitArea:{{show:true,areaStyle:{{color:['rgba(250,250,250,0.3)','rgba(200,200,200,0.1)']}}}},splitLine:{{show:true,lineStyle:{{type:'dashed',color:'#e0e0e0'}}}},axisLabel:{{fontSize:10}}}},
        {{scale:true,gridIndex:1,splitNumber:2,axisLabel:{{show:true,fontSize:10}},splitLine:{{show:false}}}}
    ],
    dataZoom:[ {{type:'inside',xAxisIndex:[0,1],start:70,end:100}}, {{type:'slider',xAxisIndex:[0,1],start:70,end:100,height:16,bottom:2,borderColor:'#ccc'}} ],
    series:[
        {{name:'K线',type:'candlestick',xAxisIndex:0,yAxisIndex:0,data:DATA.map(function(d){{return [d.open,d.close,d.low,d.high];}}),itemStyle:{{color:UP,color0:DN,borderColor:UP,borderColor0:DN}}}},
        {{name:'成交量',type:'bar',xAxisIndex:1,yAxisIndex:1,data:DATA.map(function(d,i){{return [i,d.vol,makeCloses(i)?1:-1];}}),itemStyle:{{color:function(p){{return p.value[2]>0?UP:DN;}}}}}}
    ]
}});

// ── 2. 布林带 ──
var bb = echarts.init(document.getElementById('bb-chart'));
bb.setOption({{
    animation:false,
    tooltip:{{trigger:'axis', axisPointer:{{type:'cross'}}, backgroundColor:'rgba(255,255,255,0.95)', borderColor:'#ccc', borderWidth:1, textStyle:{{color:'#333',fontSize:12}}, formatter:function(p){{return tooltipHtml(p[0].dataIndex);}} }},
    grid:{{left:'3%',right:'3%',top:8,bottom:12}},
    xAxis:{{type:'category',data:dates,axisLine:{{onZero:false}},axisTick:{{show:false}},splitLine:{{show:false}},axisLabel:{{rotate:45,fontSize:10,interval:25}}}},
    yAxis:{{scale:true,splitArea:{{show:true,areaStyle:{{color:['rgba(250,250,250,0.3)','rgba(200,200,200,0.1)']}}}},splitLine:{{show:true,lineStyle:{{type:'dashed',color:'#e0e0e0'}}}},axisLabel:{{fontSize:10}}}},
    dataZoom:[ {{type:'inside',start:70,end:100}}, {{type:'slider',start:70,end:100,height:14,bottom:0,borderColor:'#ccc'}} ],
    series:[
        {{name:'上轨',type:'line',data:bbUpper,symbol:'none',lineStyle:{{width:1,color:'#e67e22',type:'dashed'}}}},
        {{name:'中轨',type:'line',data:bbMid,symbol:'none',lineStyle:{{width:1.5,color:'#2c3e50'}}}},
        {{name:'下轨',type:'line',data:bbLower,symbol:'none',lineStyle:{{width:1,color:'#e67e22',type:'dashed'}}}},
        {{name:'收盘',type:'line',data:closes,symbol:'none',lineStyle:{{width:1.5,color:'#1a73e8'}}}}
    ]
}});

// ── 3. MACD ──
var macd = echarts.init(document.getElementById('macd-chart'));
macd.setOption({{
    animation:false,
    tooltip:{{trigger:'axis', axisPointer:{{type:'cross'}}, backgroundColor:'rgba(255,255,255,0.95)', borderColor:'#ccc', borderWidth:1, textStyle:{{color:'#333',fontSize:12}}, formatter:function(p){{return tooltipHtml(p[0].dataIndex);}} }},
    grid:{{left:'3%',right:'3%',top:8,bottom:12}},
    xAxis:{{type:'category',data:dates,axisLine:{{onZero:false}},axisTick:{{show:false}},splitLine:{{show:false}},axisLabel:{{rotate:45,fontSize:10,interval:25}}}},
    yAxis:{{scale:true,splitLine:{{show:true,lineStyle:{{type:'dashed',color:'#e0e0e0'}}}},axisLabel:{{fontSize:10}},splitArea:{{show:true,areaStyle:{{color:['rgba(250,250,250,0.3)','rgba(200,200,200,0.1)']}}}}}},
    dataZoom:[ {{type:'inside',start:70,end:100}}, {{type:'slider',start:70,end:100,height:14,bottom:0,borderColor:'#ccc'}} ],
    series:[
        {{name:'MACD',type:'line',data:DATA.map(function(d){{return d.macd;}}),symbol:'none',lineStyle:{{width:1.5,color:'#1a73e8'}}}},
        {{name:'信号',type:'line',data:DATA.map(function(d){{return d.signal;}}),symbol:'none',lineStyle:{{width:1.5,color:'#e67e22'}}}},
        {{name:'柱状',type:'bar',data:DATA.map(function(d){{return d.hist;}}),itemStyle:{{color:function(p){{return p.value>=0?UP:DN;}}}}}}
    ]
}});

// ── 4. RSI ──
var rsi = echarts.init(document.getElementById('rsi-chart'));
rsi.setOption({{
    animation:false,
    tooltip:{{trigger:'axis', axisPointer:{{type:'cross'}}, backgroundColor:'rgba(255,255,255,0.95)', borderColor:'#ccc', borderWidth:1, textStyle:{{color:'#333',fontSize:12}}, formatter:function(p){{return tooltipHtml(p[0].dataIndex);}} }},
    grid:{{left:'3%',right:'3%',top:8,bottom:12}},
    xAxis:{{type:'category',data:dates,axisLine:{{onZero:false}},axisTick:{{show:false}},splitLine:{{show:false}},axisLabel:{{rotate:45,fontSize:10,interval:25}}}},
    yAxis:{{min:0,max:100,splitLine:{{show:true,lineStyle:{{type:'dashed',color:'#e0e0e0'}}}},axisLabel:{{fontSize:10}},splitArea:{{show:true,areaStyle:{{color:['rgba(250,250,250,0.3)','rgba(200,200,200,0.1)']}}}}}},
    dataZoom:[ {{type:'inside',start:70,end:100}}, {{type:'slider',start:70,end:100,height:14,bottom:0,borderColor:'#ccc'}} ],
    series:[
        {{name:'超买70',type:'line',data:DATA.map(function(d){{return d.rsi!==null?70:null;}}),symbol:'none',lineStyle:{{width:1,color:UP,type:'dashed'}},z:1}},
        {{name:'超卖30',type:'line',data:DATA.map(function(d){{return d.rsi!==null?30:null;}}),symbol:'none',lineStyle:{{width:1,color:DN,type:'dashed'}},z:1}},
        {{name:'RSI',type:'line',data:DATA.map(function(d){{return d.rsi;}}),symbol:'none',lineStyle:{{width:2,color:'#8e44ad'}},areaStyle:{{color:{{type:'linear',x:0,y:0,x2:0,y2:1,colorStops:[{{offset:0,color:'rgba(142,68,173,0.3)'}},{{offset:0.5,color:'rgba(142,68,173,0.05)'}},{{offset:1,color:'rgba(142,68,173,0.3)'}}]}}}},z:2}}
    ]
}});

// ── 5. ATR ──
var atr = echarts.init(document.getElementById('atr-chart'));
atr.setOption({{
    animation:false,
    tooltip:{{trigger:'axis', axisPointer:{{type:'cross'}}, backgroundColor:'rgba(255,255,255,0.95)', borderColor:'#ccc', borderWidth:1, textStyle:{{color:'#333',fontSize:12}}, formatter:function(p){{return tooltipHtml(p[0].dataIndex);}} }},
    grid:{{left:'3%',right:'3%',top:8,bottom:12}},
    xAxis:{{type:'category',data:dates,axisLine:{{onZero:false}},axisTick:{{show:false}},splitLine:{{show:false}},axisLabel:{{rotate:45,fontSize:10,interval:25}}}},
    yAxis:{{scale:true,splitLine:{{show:true,lineStyle:{{type:'dashed',color:'#e0e0e0'}}}},axisLabel:{{fontSize:10}},splitArea:{{show:true,areaStyle:{{color:['rgba(250,250,250,0.3)','rgba(200,200,200,0.1)']}}}}}},
    dataZoom:[ {{type:'inside',start:70,end:100}}, {{type:'slider',start:70,end:100,height:14,bottom:0,borderColor:'#ccc'}} ],
    series:[
        {{name:'ATR(14)',type:'line',data:DATA.map(function(d){{return d.atr;}}),symbol:'none',lineStyle:{{width:2,color:'#e74c3c'}},areaStyle:{{color:{{type:'linear',x:0,y:0,x2:0,y2:1,colorStops:[{{offset:0,color:'rgba(231,76,60,0.25)'}},{{offset:1,color:'rgba(231,76,60,0.02)'}}]}}}}}},
        {{name:'ATR均线',type:'line',data:(function(){{var r=[],arr=DATA.map(function(d){{return d.atr;}});for(var i=0;i<arr.length;i++){{if(i<20||arr[i]===null){{r.push(null);}}else{{var s=0,c=0;for(var j=i-19;j<=i;j++){{if(arr[j]!==null){{s+=arr[j];c++;}}}}r.push(c>0?s/c:null);}}}}return r;}})(),symbol:'none',lineStyle:{{width:1,color:'#2c3e50',type:'dashed'}}}}
    ]
}});

// ── 6. RS ──
var rsChart = echarts.init(document.getElementById('rs-chart'));
var rsData = DATA.map(function(d){{return d.rs;}});
var rsMA20 = DATA.map(function(d){{return d.rs_ma20;}});
// RS基准线=该区间的RS均值
var rsMean = 0, rsCount = 0;
for(var i=0;i<rsData.length;i++){{if(rsData[i]!==null){{rsMean+=rsData[i];rsCount++;}}}}
rsMean = rsMean/rsCount;
var rsBaseLine = [];
for(var i=0;i<rsData.length;i++){{rsBaseLine.push(rsMean);}}

rsChart.setOption({{
    animation:false,
    tooltip:{{trigger:'axis', axisPointer:{{type:'cross'}}, backgroundColor:'rgba(255,255,255,0.95)', borderColor:'#ccc', borderWidth:1, textStyle:{{color:'#333',fontSize:12}}, formatter:function(p){{return tooltipHtml(p[0].dataIndex);}} }},
    grid:{{left:'3%',right:'3%',top:8,bottom:12}},
    xAxis:{{type:'category',data:dates,axisLine:{{onZero:false}},axisTick:{{show:false}},splitLine:{{show:false}},axisLabel:{{rotate:45,fontSize:10,interval:25}}}},
    yAxis:{{scale:true,splitLine:{{show:true,lineStyle:{{type:'dashed',color:'#e0e0e0'}}}},axisLabel:{{fontSize:10}},splitArea:{{show:true,areaStyle:{{color:['rgba(250,250,250,0.3)','rgba(200,200,200,0.1)']}}}}}},
    dataZoom:[ {{type:'inside',start:70,end:100}}, {{type:'slider',start:70,end:100,height:14,bottom:0,borderColor:'#ccc'}} ],
    series:[
        {{name:'RS均值',type:'line',data:rsBaseLine,symbol:'none',lineStyle:{{width:1,color:'#2c3e50',type:'dashed'}},z:1}},
        {{name:'RS(20)',type:'line',data:rsMA20,symbol:'none',lineStyle:{{width:1.5,color:'#e67e22'}},z:2}},
        {{name:'RS',type:'line',data:rsData,symbol:'none',lineStyle:{{width:2,color:'#1a73e8'}},areaStyle:{{color:{{type:'linear',x:0,y:0,x2:0,y2:1,colorStops:[{{offset:0,color:'rgba(26,115,232,0.25)'}},{{offset:1,color:'rgba(26,115,232,0.02)'}}]}}}},z:3}}
    ]
}});

// ── 自适应 ──
window.addEventListener('resize', function() {{ main.resize(); bb.resize(); macd.resize(); rsi.resize(); atr.resize(); rsChart.resize(); }});
</script>
</body>
</html>"""

with open(r"D:\AI\线上学习\hengrui_indicators.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("OK - HTML生成完毕")
