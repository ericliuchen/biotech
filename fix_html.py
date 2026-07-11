#!/usr/bin/env python
"""
读取 hengrui_indicators_data.json 并将其内嵌到 HTML 中
解决 file:// 协议下 fetch 被 CORS 拦截的问题
"""
import json

# 读取数据
with open(r"D:\AI\线上学习\hengrui_indicators_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 读取原HTML模板
with open(r"D:\AI\线上学习\hengrui_indicators.html", "r", encoding="utf-8") as f:
    html = f.read()

# 替换 fetch 逻辑为直接内嵌数据
old_script = """<script>
// ─── 读取数据（硬编码为减少请求） ───
// 为了减少文件大小，用 fetch 加载 JSON 数据
fetch('./hengrui_indicators_data.json')
    .then(function(r) { return r.json(); })
    .then(function(DATA) {
        renderCharts(DATA);
    })
    .catch(function(e) {
        document.body.innerHTML = '<p style="color:red;text-align:center;margin-top:40px;">加载数据失败: ' + e.message + '</p>';
    });

function renderCharts(DATA) {"""

data_json_str = json.dumps(data, ensure_ascii=False)

new_script = f"""<script>
// ─── 数据（已内嵌，无需 fetch） ───
var DATA = {data_json_str};

// ─── 渲染函数 ───
function renderCharts(DATA) {{"""

if old_script in html:
    html = html.replace(old_script, new_script)
    with open(r"D:\AI\线上学习\hengrui_indicators.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ 修复完成！数据已内嵌到 HTML 中，直接双击打开即可。")
else:
    print("❌ 未找到匹配的脚本片段，请检查 HTML 文件。")
    # 调试：打印部分内容
    print("--- 期望 ---")
    print(repr(old_script[:100]))
    print("--- 实际 ---")
    print(repr(html[html.find("<script>"):html.find("<script>")+150]))
