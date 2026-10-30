"""Render a normalized health dataset as a portable, offline Chinese HTML report.

Public API: render_report(data: dict) -> str. No dependencies or network access.
CLI: python render.py input.json -o report.html
The caller owns parsing, daily aggregation, source selection and clinical claims.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def render_report(data: dict) -> str:
    """Return a self-contained report; do not mutate data or write files.

    Optional contract fields may be omitted. Non-finite JSON numbers are rejected
    rather than silently presented as measurements. External strings are embedded
    only in escaped JSON and inserted into the DOM using textContent.
    """
    if not isinstance(data, dict):
        raise TypeError("data must be a dictionary")
    payload = json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    for character, escaped in (
        ("&", "\\u0026"), ("<", "\\u003c"), (">", "\\u003e"),
        (" ", "\\u2028"), (" ", "\\u2029"),
    ):
        payload = payload.replace(character, escaped)
    return _HTML.replace("__REPORT_DATA__", payload)


_HTML = r'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="referrer" content="no-referrer">
<title>Apple Health · 健康记录</title>
<style>
:root{color-scheme:light;--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--secondary:#52514e;--line:#e1e0d9;--series:#2a78d6;--warning:#fab219;--quality:#ec835a;--wash:#f0efec}
:root[data-theme=dark]{color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--ink:#ffffff;--secondary:#c3c2b7;--line:#383835;--series:#3987e5;--wash:#252523}
*{box-sizing:border-box}body{margin:0;background:var(--page);color:var(--ink);font:15px/1.7 system-ui,-apple-system,"PingFang SC","Microsoft YaHei","Noto Sans CJK SC","WenQuanYi Zen Hei","Segoe UI",sans-serif}button,input,select{font:inherit;color:inherit}button,select,input{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:8px 12px;min-height:42px}button,summary{cursor:pointer}button:hover{background:var(--wash)}button:disabled{opacity:.45;cursor:default}:focus-visible{outline:3px solid var(--series);outline-offset:4px}a{color:inherit;text-underline-offset:4px}main{max-width:1200px;margin:auto;padding:32px 32px 70px}.masthead{display:flex;align-items:center;justify-content:space-between;gap:20px;border-bottom:1px solid var(--ink);padding-bottom:18px}.wordmark{font-size:12px;letter-spacing:.16em;font-weight:650}.actions{display:flex;gap:8px}.actions button{white-space:nowrap}h1{font-size:clamp(36px,6vw,66px);line-height:1.17;letter-spacing:-.045em;margin:14px 0 20px;font-weight:650}h2{font-size:24px;line-height:1.4;letter-spacing:-.025em;margin:0}h3{font-size:18px;margin:0}p{margin:9px 0}small,.muted{color:var(--secondary)}.period{font-size:14px;margin-top:24px}.fixed-label{font-size:12px;color:var(--secondary)}.findings{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.finding{padding:22px;background:var(--surface);border:1px solid var(--line);border-radius:12px;overflow-wrap:anywhere}.status{display:flex;gap:8px;align-items:center;font-size:12px;color:var(--secondary);margin-bottom:10px}.status-mark{width:9px;height:9px;background:var(--secondary);border-radius:50%}.attention .status-mark{background:var(--warning)}.quality .status-mark{background:var(--quality)}.finding p{font-size:14px;color:var(--secondary);white-space:pre-wrap}.provenance{border:1px solid var(--line);border-radius:12px;margin:24px 0 40px;background:var(--surface);padding:16px 20px}summary{font-weight:600}.details-body{padding-top:16px}.details-grid{display:grid;grid-template-columns:1fr 1fr;gap:28px}.facts{display:grid;grid-template-columns:120px minmax(0,1fr);gap:8px 16px;font-size:13px;margin:16px 0}.facts dt{color:var(--secondary)}.facts dd{margin:0;overflow-wrap:anywhere}.source-list li{margin-bottom:12px}.source-list small{display:block}.caveat{border-left:3px solid var(--line);padding-left:16px;font-size:14px;color:var(--secondary);margin:20px 0}.filters{display:flex;align-items:end;gap:12px;flex-wrap:wrap;padding:18px 0;border-top:1px solid var(--ink);border-bottom:1px solid var(--line)}label{display:flex;flex-direction:column;gap:4px;font-size:12px;color:var(--secondary)}.custom{display:flex;gap:10px;align-items:end;flex-wrap:wrap}.filter-status{font-size:13px;color:var(--secondary);margin:14px 0 24px}.error{font-weight:600}.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;margin-bottom:34px}.kpi{padding:20px 0;border-top:2px solid var(--line)}.kpi-label{font-size:13px;color:var(--secondary)}.kpi-value{font-size:34px;line-height:1.2;letter-spacing:-.035em;margin:12px 0}.kpi-value small{font-size:14px;letter-spacing:0;margin-left:7px}.kpi p{font-size:12px;color:var(--secondary)}.chart-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px}.card{border:1px solid var(--line);background:var(--surface);border-radius:16px;padding:24px;min-width:0}.card-head{display:flex;justify-content:space-between;align-items:start;gap:12px}.unit{font-size:12px;color:var(--secondary);white-space:nowrap}.plot{position:relative;margin:14px 0 0}.plot svg{display:block;width:100%;height:auto;overflow:visible;touch-action:pan-y}.plot text{fill:var(--secondary);font-size:12px;font-variant-numeric:tabular-nums}.grid{stroke:var(--line);stroke-width:1}.trace{fill:none;stroke:var(--series);stroke-width:2;stroke-linejoin:round;stroke-linecap:round}.dot{fill:var(--series);stroke:var(--surface);stroke-width:2}.crosshair{stroke:var(--secondary);stroke-width:1}.tooltip{position:absolute;z-index:2;width:max-content;max-width:min(290px,95%);padding:10px 13px;background:var(--surface);border:1px solid var(--line);border-radius:8px;box-shadow:0 8px 24px #0002;font-size:12px;pointer-events:none;overflow-wrap:anywhere}.tooltip strong{font-size:17px;display:block}.tooltip p{margin:3px 0}.chart-note{font-size:12px;color:var(--secondary);margin:12px 0}.table-panel{margin-top:16px;border-top:1px solid var(--line);padding-top:14px}.table-panel summary{font-size:13px}.table-scroll{overflow:auto;max-width:100%}table{width:100%;border-collapse:collapse;font-size:12px;font-variant-numeric:tabular-nums;text-align:left}caption{text-align:left;color:var(--secondary);padding:12px 0}th,td{padding:6px 10px;border-bottom:1px solid var(--line);vertical-align:top;overflow-wrap:anywhere}th{color:var(--secondary);font-weight:600}td:first-child,th:first-child{white-space:nowrap;padding-left:0}td:last-child{max-width:180px}.pagination{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:12px;font-size:12px}.pagination button{min-height:36px;padding:5px 10px}.empty{padding:35px 12px;text-align:center;color:var(--secondary)}footer{border-top:1px solid var(--line);margin-top:40px;padding-top:20px;font-size:12px;color:var(--secondary)}[hidden]{display:none!important}.skip{position:absolute;left:10px;top:-80px;background:var(--surface);padding:12px;z-index:10}.skip:focus{top:10px}
@media(max-width:850px){.findings{grid-template-columns:1fr}.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.details-grid{grid-template-columns:1fr}}
@media(max-width:620px){main{padding:20px 16px 40px}.chart-grid{grid-template-columns:1fr}.card{padding:18px 14px}.masthead{align-items:start}.actions button{padding:6px 9px;font-size:12px}.facts{grid-template-columns:95px minmax(0,1fr)}.kpi-value{font-size:29px}.custom input{max-width:155px}.card-head h3{font-size:17px}}
@media(forced-colors:active){.trace{stroke:CanvasText}.dot{fill:CanvasText;stroke:Canvas}.crosshair,.grid{stroke:CanvasText}.end-label{stroke:Canvas}.status-mark{border:2px solid CanvasText}}
@media print{:root,:root[data-theme=dark]{color-scheme:light;--page:#fff;--surface:#fff;--ink:#000;--secondary:#444;--line:#ccc;--series:#222;--wash:#eee}main{max-width:none;padding:0}.actions,.filters,.skip,.tooltip,.pagination{display:none!important}h1{font-size:38px}.chart-grid{display:block}.card{break-inside:avoid;margin-bottom:18px}.plot{max-width:850px}.kpis{grid-template-columns:repeat(4,1fr)}.finding{break-inside:avoid}.provenance{break-inside:auto}.table-scroll{overflow:visible}a{text-decoration:none}.chart-note{color:#444}footer{margin-top:18px}}
/* Dashboard layout. Chart colors use the validated single-blue palette in both modes. */
:root { --page:#f3f4f6; --line:#e5e6e8; --wash:#eef1f5; }
:root[data-theme=dark] { --page:#111214; --line:#303235; --wash:#25272b; }
body { font-size:14px; line-height:1.55; -webkit-font-smoothing:antialiased; }
main { max-width:1440px; padding:24px 32px 32px; }
button, select, input { min-height:36px; padding:6px 11px; font-size:12px; }
.masthead { border:0; padding:0 0 14px; align-items:flex-start; }
.brand { display:flex; align-items:center; gap:12px; }
.brand-mark { width:36px; height:36px; border-radius:11px; background:var(--surface); border:1px solid var(--line); display:grid; place-items:center; }
.brand-mark svg { width:22px; height:22px; fill:none; stroke:var(--series); stroke-width:2; }
h1 { font-size:25px; line-height:1.2; letter-spacing:-.035em; margin:0; font-weight:650; }
.wordmark { font-size:10px; letter-spacing:.13em; color:var(--secondary); }
h2 { font-size:17px; } h3 { font-size:14px; font-weight:600; }
.period { margin:5px 0 0; font-size:11px; color:var(--secondary); }
.synthetic { padding:9px 14px; border:1px dashed var(--secondary); border-radius:10px; margin-bottom:12px; font-size:12px; }
.finding-strip { display:flex; align-items:center; gap:12px; padding:10px 14px; border:1px solid var(--line); background:var(--surface); border-radius:12px; margin-bottom:8px; }
.finding-strip > div { min-width:0; flex:1; }
.finding-strip p { margin:2px 0 0; font-size:12px; }
.finding-strip .status-mark { flex-shrink:0; background:var(--warning); }
.finding-strip .status-mark.neutral { background:var(--secondary); }
.fixed-label { font-size:10px; }
.finding-details { margin:0 0 10px; font-size:12px; }
.findings { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px; padding-top:10px; }
.finding { padding:14px; border-radius:10px; }
.finding p { font-size:12px; }
.finding h3 { font-size:13px; }
.status { margin-bottom:5px; font-size:11px; }
.provenance { padding:11px 14px; border-radius:12px; margin:0 0 14px; font-size:12px; }
.provenance h3 { margin-top:12px; }
.details-grid { gap:24px; }
.filters { border:0; background:var(--surface); border-radius:12px; padding:10px 14px; gap:14px; align-items:center; box-shadow:0 1px 2px #00000004; }
.filters > label { flex-direction:row; align-items:center; gap:10px; }
.filter-hint { font-size:11px; color:var(--secondary); margin-left:auto; }
.filter-status { font-size:11px; margin:9px 2px 13px; }
.kpis { gap:12px; margin-bottom:15px; }
.kpi { background:var(--surface); border:1px solid var(--line); border-radius:13px; padding:13px 16px; }
.kpi-label { font-size:11px; display:flex; align-items:center; gap:7px; }
.metric-key { width:12px; height:3px; border-radius:2px; background:var(--series); flex-shrink:0; }
.kpi-value { font-size:29px; font-weight:600; margin:8px 0 3px; line-height:1.1; }
.kpi-value small { font-size:11px; font-weight:400; }
.kpi p { margin:5px 0 0; font-size:10px; }
.tabs { display:flex; gap:5px; overflow:auto; padding:0 0 12px; scrollbar-width:thin; }
.tabs button { border:0; background:transparent; white-space:nowrap; border-radius:8px; font-size:12px; }
.tabs button[aria-selected=true] { background:var(--ink); color:var(--surface); }
.tab-count { margin-left:6px; opacity:.65; font-size:10px; }
.chart-grid { grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; align-items:start; }
.card { grid-column:auto; padding:16px 16px 10px; border-radius:14px; box-shadow:0 2px 6px #00000002; }
.card-head { align-items:center; }
.card-head h3 { font-size:13px; }
.unit { font-size:10px; }
.metric-number { font-size:26px; line-height:1.15; margin:8px 0 0; letter-spacing:-.035em; font-weight:600; }
.metric-number small { font-size:11px; margin-left:6px; color:var(--secondary); font-weight:400; letter-spacing:0; }
.metric-context { font-size:10px; color:var(--secondary); margin:3px 0 0; }
.plot { margin-top:3px; }
.plot svg { height:auto; aspect-ratio:400 / 176; }
.plot text { font-size:10px; }
.trace { vector-effect:non-scaling-stroke; }
/* A surface halo keeps the endpoint value readable where it crosses the line. */
.end-label { paint-order:stroke; stroke:var(--surface); stroke-width:4px; stroke-linejoin:round; }
.grid { stroke-opacity:.75; }
.chart-note { margin:6px 0; font-size:11px; }
.sr-only { position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden; clip:rect(0,0,0,0); white-space:nowrap; border:0; }
.metric-details { margin-top:6px; padding-top:8px; border-top:1px solid var(--line); font-size:11px; }
.metric-details > summary { font-size:10px; font-weight:400; color:var(--secondary); }
.table-panel { margin:10px 0 0; padding-top:8px; }
.table-panel summary { font-size:11px; }
.empty { padding:12px 0; margin:0; text-align:left; font-size:12px; }
.card.no-data { min-height:0; }
.coverage-panel { grid-column:1/-1; padding:18px; background:var(--surface); border:1px solid var(--line); border-radius:14px; }
.coverage-panel > a { display:inline-block; margin:0 0 10px; font-size:12px; }
.coverage-counts { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; margin:12px 0; }
.coverage-counts > div { border:1px solid var(--line); padding:10px; border-radius:8px; }
.coverage-counts strong { display:block; font-size:22px; font-weight:600; }
.coverage-counts small { font-size:11px; }
.coverage-table { min-width:650px; }
.coverage-table td { max-width:260px; }
.coverage-table details { max-width:340px; }
.source-item { padding:6px 0; border-bottom:1px solid var(--line); }
footer { margin-top:22px; padding-top:14px; font-size:10px; }
@media(max-width:1050px) { .chart-grid { grid-template-columns:repeat(2,minmax(0,1fr)); } .findings { grid-template-columns:1fr; } }
@media(max-width:700px) {
  main { padding:18px 14px 30px; }
  .masthead { gap:8px; } h1 { font-size:21px; }
  .brand-mark { display:none; }
  .actions { gap:5px; } .actions button { font-size:10px; padding:5px 8px; }
  .kpis { grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; }
  .kpi { padding:12px; } .kpi-value { font-size:26px; }
  .filter-hint { margin-left:0; }
  .chart-grid { grid-template-columns:1fr; }
  .coverage-counts { grid-template-columns:repeat(2,minmax(0,1fr)); }
  .finding-strip { gap:8px; } .fixed-label { display:block; }
}
@media print {
  main { padding:0; } .tabs { display:none; } .chart-grid { display:grid; grid-template-columns:1fr 1fr; }
  .card { box-shadow:none; } .coverage-panel { grid-column:1/-1; }
  .kpi { break-inside:avoid; } .finding-strip { break-inside:avoid; }
}
</style>
</head>
<body>
<a class="skip" href="#explore">跳至趋势探索</a>
<main>
<header class="masthead">
  <div><div class="brand"><span class="brand-mark" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M2 12h5l3-7 4 14 3-7h5"/></svg></span><div><div class="wordmark">APPLE HEALTH / OFFLINE</div><h1>健康记录</h1></div></div><p id="report-period" class="period"></p></div>
  <div class="actions"><button id="theme" type="button">切换深色</button><button id="print" type="button">打印 / PDF</button></div>
</header>
<div id="synthetic" class="synthetic" hidden>完全虚构示例 · 所有数值为合成数据，不来自任何个人，不描述真实健康状况。</div>
<section aria-label="固定范围阅读线索">
  <div class="finding-strip"><span id="finding-mark" class="status-mark" aria-hidden="true"></span><div><span id="fixed-period" class="fixed-label"></span><p id="finding-headline"></p></div></div>
  <details class="finding-details"><summary id="findings-summary">证据与边界</summary><div id="findings" class="findings"></div></details>
</section>
<details class="provenance" id="methodology"><summary>完整导出与来源选择 <span id="inventory-summary" class="muted"></span> · 固定范围</summary><div class="details-body"><div id="full-coverage"></div><div class="details-grid"><section><h3>来源与处理</h3><dl class="facts" id="meta"></dl><h3>如何阅读</h3><ul><li>每条曲线只使用一个纵轴；纵轴随数据范围调整，非健康阈值。</li><li>日值沿用输入：sum 表示当日累计量，median 表示当日中位数，min 表示最低采样。主睡眠另以最长会话实睡时长定义。</li><li>长时间段按周或月展示有记录日的日值均值，不累计跨月总量；最低采样指标保留区间最低值。均值不是原始样本加权均值。缺失日不补零、不插值；曲线在缺失处断开。</li><li>覆盖率＝有有效日值的天数 / 筛选区间日历天数。n 为上游提供的样本量，不等同于佩戴时长；缺失的 n 不推算。</li><li>来源与佩戴方式变化可能影响可比性；关联不代表因果。睡眠按上游定义归属日期，本报告不重建睡眠区间。</li></ul></section><section><h3>数据质量</h3><ul id="quality"></ul><h3>导出清单与运动记录</h3><div id="inventory"></div><div id="workouts"></div><h3>参考来源</h3><ol id="sources" class="source-list"></ol></section></div><p class="caveat">本报告仅用于个人记录整理与趋势观察，不提供诊断、风险评分或治疗建议。可穿戴设备测量不能替代临床检查；如有不适或持续异常，请咨询合格医疗专业人员。参考来源由输入数据提供，本渲染器不联网核验。</p></div></details>
<section id="explore" aria-label="筛选范围内的健康记录">
<form id="filters" class="filters">
  <label>日期范围<select id="range"><option value="focus" selected>核心记录时段</option><option value="30">最近 30 天</option><option value="90">最近 90 天</option><option value="365">最近 365 天</option><option value="all">全部记录</option><option value="custom">自定义范围</option></select></label>
  <label>数据来源<select id="source-filter"><option value="default">默认来源（逐指标）</option></select></label>
  <div class="custom" id="custom" hidden><label>起始日期<input id="start" type="date" required></label><label>结束日期<input id="end" type="date" required></label><button type="submit">应用范围</button></div>
  <span class="filter-hint">下方图表随日期与来源变化；来源之间不相加</span>
</form>
<p id="filter-status" class="filter-status" role="status" aria-live="polite"></p>
<div id="kpis" class="kpis"></div>
<nav id="tabs" class="tabs" role="tablist" aria-label="指标分类"></nav>
<div id="charts" class="chart-grid" role="tabpanel" tabindex="0"></div>
</section>
<footer>本地生成 · 单文件离线报告 · 无远程字体、脚本、网络请求或遥测。图表可使用左右方向键逐点阅读，Home / End 跳到首末点；原始日值见各卡片的数据表。打印保留当前筛选范围，日表仅打印已展开的当前页。</footer>
<noscript><p class="caveat">需要启用 JavaScript 才能读取内嵌数据并绘制报告；无需联网。</p></noscript>
</main>
<script id="report-data" type="application/json">__REPORT_DATA__</script>
<script>
'use strict';
(() => {
const data=JSON.parse(document.getElementById('report-data').textContent);
const obj=v=>v&&typeof v==='object'&&!Array.isArray(v)?v:{};
const arr=v=>Array.isArray(v)?v:[];
const meta=obj(data.meta), DAY=86400000;
if (meta.synthetic) {
  document.title = '完全虚构示例｜Apple Health 分析';
  document.getElementById('synthetic').hidden = false;
}
const $=id=>document.getElementById(id);
const text=v=>v===undefined||v===null||v===''?'未提供':typeof v==='object'?JSON.stringify(v):String(v);
const numeric=v=>typeof v==='number'&&Number.isFinite(v);
const fmt=(v,d=1)=>numeric(v)?v.toLocaleString('zh-CN',{maximumFractionDigits:d}):'—';
function el(tag,content,cls){const e=document.createElement(tag);if(content!==undefined)e.textContent=text(content);if(cls)e.className=cls;return e;}
function day(v){if(typeof v!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(v))return null;const t=Date.parse(v+'T00:00:00Z');return Number.isFinite(t)&&new Date(t).toISOString().slice(0,10)===v?t:null;}
const iso=t=>new Date(t).toISOString().slice(0,10);
const mean=rs=>rs.length?rs.reduce((s,r)=>s+r.value,0)/rs.length:null;
const nsum=rs=>{const known=rs.filter(r=>numeric(r.n)&&r.n>=0);return known.length?fmt(known.reduce((s,r)=>s+r.n,0),0)+(known.length<rs.length?'（部分未知）':''):'未知';};
const sources=rs=>[...new Set(rs.map(r=>text(r.source)))].join('、');
let rejected=0, repeated=0;
const order=['sleep','spo2_min','resting_hr','steps','spo2','hrv','hrv_rmssd','respiratory','exercise','active_energy','vo2','heart_rate'];
const defaults={sleep:'睡眠',resting_hr:'静息心率',hrv:'心率变异性',steps:'步数',exercise:'锻炼时间',active_energy:'活动能量',spo2:'血氧',respiratory:'呼吸频率',weight:'体重',vo2:'心肺适能',heart_rate:'心率'};
const metrics=arr(data.metrics).map((raw,index)=>{
 const m=obj(raw),unit=String(m.unit||''),u=unit.toLowerCase().trim();
 const factor=m.id==='sleep'&&['min','minute','minutes','分钟'].includes(u)?1/60:m.id==='sleep'&&['s','sec','second','seconds','秒'].includes(u)?1/3600:1;
 const hours=m.id==='sleep'&&(factor!==1||['h','hr','hour','hours','小时'].includes(u));
 function normalizeRows(rawRows) {
   const byDate = new Map();
   for (const rawRow of arr(rawRows)) {
     const r = obj(rawRow), t = day(r.date);
     if (t === null || !numeric(r.value)) { rejected++; continue; }
     if (byDate.has(t)) repeated++;
     byDate.set(t, {...r, t, value:r.value*factor,
       min:numeric(r.min)?r.min*factor:null, max:numeric(r.max)?r.max*factor:null});
   }
   return [...byDate.values()].sort((a,b)=>a.t-b.t);
 }
 const series = Object.fromEntries(Object.entries(obj(m.source_series)).map(([key, rows]) => [key, normalizeRows(rows)]));
 // Oxygen nadirs must never become means when the display is coarsened.
 return {...m,index,kind:m.id==='spo2_min'?'min':m.kind,label:m.label||defaults[m.id]||m.id||'未命名指标',unit:hours?'小时':unit,rows:normalizeRows(m.rows),series};
}).sort((a,b)=>{const rank=m=>order.includes(m.id)?order.indexOf(m.id):order.length;return rank(a)-rank(b)||a.index-b.index;});
const sourceLabel = source => source.replace(/^Watch /, '手表 ').replace(/^Phone /, '手机 ').replace(/^Other /, '其他来源 ').replace(/^Workout$/, '训练记录');
const sourceNames = [...new Set(metrics.flatMap(m=>Object.keys(m.series)))].sort();
for (const name of sourceNames) {
  const option = el('option', sourceLabel(name)); option.value = name;
  $('source-filter').append(option);
}
const dates=metrics.flatMap(m=>[...m.rows,...Object.values(m.series).flat()].map(r=>r.t));
const minDate=dates.reduce((a,b)=>Math.min(a,b),Infinity),maxDate=dates.reduce((a,b)=>Math.max(a,b),-Infinity);
let fullStart=day(meta.start),fullEnd=day(meta.end);
if(fullStart===null)fullStart=Number.isFinite(minDate)?minDate:null;
if(fullEnd===null)fullEnd=Number.isFinite(maxDate)?maxDate:fullStart;
if(fullStart===null)fullStart=fullEnd;
const validBounds=fullStart!==null&&fullEnd!==null&&fullStart<=fullEnd;
const period=validBounds?iso(fullStart)+' — '+iso(fullEnd):'报告日期未提供或范围无效';
let generated=text(meta.generated_at);try{generated=new Date(meta.generated_at).toLocaleString('zh-CN',{timeZone:meta.timezone,hour12:false});}catch{}
$('report-period').textContent = '完整原始记录 '+period+' · '+text(meta.timezone);
$('fixed-period').textContent = '固定范围 · 默认来源 · '+period+' · 不随筛选变化';
const labels = {attention:'! 关注线索', info:'i 记录观察', quality:'! 质量提示'};
const findings = arr(data.findings).map(obj);
const caution = findings.filter(f => f.level === 'attention');
const qualityFindings = findings.filter(f => f.level === 'quality');
const priority = caution.length ? caution : qualityFindings.length ? qualityFindings : findings;
$('finding-mark').classList.toggle('neutral', !caution.length && !qualityFindings.length);
// Every attention title remains visible; the original bodies stay in the disclosure.
$('finding-headline').textContent = priority.length
  ? (caution.length ? '! 需关注：' : qualityFindings.length ? '! 质量提示：' : '记录观察：') + priority.map(f => text(f.title)).join('；')
  : '未提供固定范围解读；图表仅呈现记录，不自动生成医学结论。';
$('findings-summary').textContent = '证据与边界 · '+findings.length+' 条观察';
for (const f of findings) {
  const level = Object.hasOwn(labels, f.level) ? f.level : 'info';
  const card = el('article', undefined, 'finding '+level);
  const status = el('div', undefined, 'status');
  status.append(el('span', undefined, 'status-mark'), el('span', labels[level]));
  card.append(status, el('h3', f.title || '记录线索'), el('p', f.body || '未提供说明'));
  if (f.start || f.end) card.append(el('small', [f.start, f.end].filter(Boolean).join(' — ')));
  $('findings').append(card);
}
const metaFields=[['export_date','导出日期'],['timezone','时间口径'],['records','原始记录数'],['duplicates','上游重复数'],['invalid','上游无效数'],['source_policy','来源选择策略'],['input_sha256','输入 SHA-256']];
for(const [key,label] of metaFields)$('meta').append(el('dt',label),el('dd',text(meta[key])));
$('meta').append(el('dt', '报告生成时间'), el('dd', generated));
for(const q of arr(data.quality))$('quality').append(el('li',q));
if(rejected)$('quality').append(el('li','展示层忽略 '+rejected+' 条无效日期或非数值日记录；不填零。'));
if(repeated)$('quality').append(el('li','输入存在 '+repeated+' 条同指标同日期重复日值；展示层保留最后一条有效日值，请核查上游聚合。'));
if(!$('quality').children.length)$('quality').append(el('li','输入未提供质量提示；这不代表数据完整或无误。'));
const inv=arr(data.inventory);if(inv.length){const list=el('ul');for(const raw of inv){const item=obj(raw);list.append(el('li',text(item.type)+' · '+text(item.count)+' 条'));}$('inventory').append(list);}else $('inventory').append(el('p','未提供导出类型清单。','muted'));
// Inventory and source counts describe the full export, not a clinical coverage rate.
const coverage = obj(data.coverage);
const coverageItems = arr(coverage.items).map(obj);
const analyzedItems = coverageItems.filter(item => item.status === 'analyzed');
const totalTypes = numeric(coverage.total_types) ? coverage.total_types : inv.length;
const analyzedTypes = numeric(coverage.analyzed_types) ? coverage.analyzed_types : analyzedItems.length;
$('inventory-summary').textContent = '· '+fmt(totalTypes, 0)+' 类原始类型 / '+(coverageItems.length ? fmt(analyzedTypes, 0) : '未知')+' 类进入分析 / '+metrics.length+' 项指标';
const fullCoverage = $('full-coverage');
fullCoverage.append(el('h3', '完整导出 → 全来源独立处理 → 默认视图'));
const counts = el('div', undefined, 'coverage-counts');
for (const [label, value] of [
  ['原始 Record 行', coverage.total_records ?? meta.records],
  ['全部来源有效去重行', coverage.processed_records],
  ['默认来源有效去重行', coverage.selected_records],
  ['仅清点的原始类型', coverageItems.length ? totalTypes - analyzedTypes : null],
]) {
  const tile = el('div');
  tile.append(el('strong', fmt(value, 0)), el('small', label));
  counts.append(tile);
}
fullCoverage.append(counts, el('p', '固定完整导出范围。各来源独立处理，可在下拉框切换；默认行只是初始视图。有效处理包含按口径筛选的睡眠状态，不等于每行都进入主图，更不是临床覆盖率。', 'chart-note'));
if (coverageItems.length) {
  const scroll = el('div', undefined, 'table-scroll');
  const table = el('table', undefined, 'coverage-table');
  table.append(el('caption', '每个原始类型均列出；来源独立聚合，默认展示一个来源，不拼接或相加。'));
  const head = el('thead'), row = el('tr'), body = el('tbody');
  for (const label of ['原始类型', '处理状态', '原始 / 全来源有效 / 默认', '来源与原因']) {
    const cell = el('th', label); cell.scope = 'col'; row.append(cell);
  }
  head.append(row);
  for (const item of coverageItems) {
    const tr = el('tr'), name = el('td');
    name.append(el('strong', item.label || item.type), el('div', item.type, 'muted'));
    const details = el('details');
    details.append(el('summary', '选定：'+(item.selected_source || '未选择')));
    details.append(el('p', item.reason || '未提供处理说明'));
    for (const source of arr(item.available_sources).map(obj)) {
      details.append(el('div', text(source.source)+' · '+fmt(source.records, 0)+' 条 · '+text(source.start)+' — '+text(source.end), 'source-item'));
    }
    const sourceCell = el('td'); sourceCell.append(details);
    tr.append(name, el('td', item.status === 'analyzed' ? '已进入分析' : '仅清点 · 未分析'), el('td', fmt(item.total_records, 0)+' / '+fmt(item.processed_records, 0)+' / '+fmt(item.selected_records, 0)), sourceCell);
    body.append(tr);
  }
  table.append(head, body); scroll.append(table); fullCoverage.append(scroll);
} else {
  fullCoverage.append(el('p', '输入未提供逐类型分析覆盖；完整类型清单不代表所有数据都已分析。', 'chart-note'));
}
const w=obj(data.workouts);$('workouts').append(el('p','固定范围运动记录：'+text(w.count)+' 次 · '+text(w.minutes)+' 分钟。此分类汇总固定；活动与训练页的每日训练时长／次数可筛选。','muted'));
if(arr(w.by_type).length){const list=el('ul');arr(w.by_type).forEach(raw=>{const item=obj(raw);list.append(el('li',text(item.type)+' · '+text(item.count)+' 次 / '+text(item.minutes)+' 分钟'));});$('workouts').append(list);}
arr(data.sources).forEach(raw=>{const s=obj(raw),item=el('li');let url;try{url=new URL(s.url);}catch{}if(url&&['https:','http:'].includes(url.protocol)){const a=el('a',s.title||url.hostname);a.href=url.href;a.target='_blank';a.rel='noopener noreferrer';item.append(a);}else item.append(el('span',s.title||'参考来源'));item.append(el('small','核验日期：'+text(s.checked)),el('p',s.claim||'未提供引用范围'));$('sources').append(item);});
if(!$('sources').children.length)$('sources').append(el('li','未提供外部参考来源。'));
function setTheme(dark){document.documentElement.dataset.theme=dark?'dark':'light';$('theme').textContent=dark?'切换浅色':'切换深色';$('theme').setAttribute('aria-pressed',String(dark));}
setTheme(window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches);
$('theme').onclick=()=>setTheme(document.documentElement.dataset.theme!=='dark');
$('print').onclick=()=>window.print();
function tableView(rows,m){
 const details=el('details',undefined,'table-panel');details.append(el('summary','查看每日数据 · '+rows.length+' 天'));
 let initialized=false,page=0;const size=20,wrap=el('div',undefined,'table-scroll'),table=el('table');table.append(el('caption','筛选范围内的日值，按日期倒序；min / max 为上游日内范围。'));
 const head=el('thead'),tr=el('tr');['日期','日值 ('+(m.unit||'未标单位')+')','n','min','max','来源'].forEach(t=>{const th=el('th',t);th.scope='col';tr.append(th);});head.append(tr);const body=el('tbody');table.append(head,body);wrap.append(table);
 const nav=el('div',undefined,'pagination'),prev=el('button','上一页'),next=el('button','下一页'),info=el('span');prev.type=next.type='button';info.setAttribute('aria-live','polite');nav.append(prev,info,next);
 function draw(){body.replaceChildren();const count=Math.max(1,Math.ceil(rows.length/size));page=Math.max(0,Math.min(page,count-1));rows.slice(Math.max(0,rows.length-(page+1)*size),rows.length-page*size).reverse().forEach(r=>{const row=el('tr');[r.date,fmt(r.value,2),numeric(r.n)?fmt(r.n,0):'未知',fmt(r.min,2),fmt(r.max,2),text(r.source)].forEach(v=>row.append(el('td',v)));body.append(row);});info.textContent=(page+1)+' / '+count+' 页 · 每页 '+size+' 天';prev.disabled=page===0;next.disabled=page===count-1;}
 prev.onclick=()=>{page--;draw();};next.onclick=()=>{page++;draw();};details.addEventListener('toggle',()=>{if(details.open&&!initialized){initialized=true;details.append(wrap,nav);draw();}});return details;
}
function aggregate(rows,span,kind){
 const mode=span>730?'month':span>180?'week':'day',points=[];let group=[];
 const key=r=>mode==='month'?r.date.slice(0,7):mode==='week'?Math.floor((r.t+3*DAY)/(7*DAY)):r.date;
 function flush(){if(!group.length)return;const first=group[0],last=group[group.length-1];points.push({t:(first.t+last.t)/2,first:first.t,last:last.t,value:kind==='min'?Math.min(...group.map(r=>r.value)):mean(group),rows:group,n:nsum(group),source:sources(group)});group=[];}
 for(const r of rows){const prev=group[group.length-1];if(prev&&(key(prev)!==key(r)||r.t-prev.t!==DAY))flush();group.push(r);}flush();return {points,mode};
}
function chart(rows,m,start,end){
 const box=el('div',undefined,'plot');if(!rows.length){box.append(el('p','此范围没有有效记录；缺失不等于零。','empty'));return box;}
 const span=Math.round((end-start)/DAY)+1,{points,mode}=aggregate(rows,span,m.kind);
 const pooled=m.kind==='min'?'区间最低日值':'有记录日日值均值';
 const modeText=mode==='day'?'逐日值':mode==='week'?'按自然周（周一开始）的'+pooled:'按自然月的'+pooled;
 const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');
 // A stable viewBox gives every small multiple the same visual rhythm.
 const W=400,H=176,L=48,R=14,T=22,B=30,PW=W-L-R,PH=H-T-B;
 svg.setAttribute('viewBox',`0 0 ${W} ${H}`);svg.setAttribute('tabindex','0');svg.setAttribute('role','img');svg.setAttribute('aria-label',text(m.label)+'，'+modeText+'；左右方向键逐点阅读，Home 和 End 跳至首末点，Escape 关闭提示。');
 function node(tag,attrs={},value){const e=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,String(v)));if(value!==undefined)e.textContent=value;svg.append(e);return e;}
 node('title',{},text(m.label)+' · '+modeText);
 let low=points.reduce((a,p)=>Math.min(a,p.value),Infinity),high=points.reduce((a,p)=>Math.max(a,p.value),-Infinity);
 const pad=(high-low)*.12||Math.max(Math.abs(high)*.05,.5);low-=pad;high+=pad;
 const rawStep=(high-low)/4,power=10**Math.floor(Math.log10(rawStep)),ratio=rawStep/power,step=(ratio<=1?1:ratio<=2?2:ratio<=5?5:10)*power;
 low=Math.floor(low/step)*step;high=Math.ceil(high/step)*step;if(points.every(p=>p.value>=0))low=Math.max(0,low);
 const x=t=>L+(end===start?PW/2:(t-start)/(end-start)*PW),y=v=>T+(high-v)/(high-low)*PH;
 for(let i=0;i<=10;i++){const value=low+i*step;if(value>high+step*.01)break;const yy=y(value);node('line',{x1:L,x2:W-R,y1:yy,y2:yy,class:'grid'});node('text',{x:L-10,y:yy+4,'text-anchor':'end'},fmt(value,Math.min(6,Math.max(0,-Math.floor(Math.log10(step))))));}
 const ticks=span<=1?[start]:W<420?[start,end]:[start,start+(end-start)/2,end];ticks.forEach((t,i)=>node('text',{x:x(t),y:H-15,'text-anchor':i===0?'start':i===ticks.length-1?'end':'middle'},iso(t)));
 let path='';points.forEach((p,i)=>{const prev=points[i-1],join=prev&&p.first-prev.last===DAY;path+=(join?'L':'M')+x(p.t).toFixed(2)+' '+y(p.value).toFixed(2)+' ';});node('path',{d:path,class:'trace'});
 // One path for markers keeps even a very sparse multi-year series inexpensive.
 let dots='';points.forEach((p,i)=>{const isolated=(!points[i-1]||p.first-points[i-1].last!==DAY)&&(!points[i+1]||points[i+1].first-p.last!==DAY);if(points.length<=24||isolated||i===points.length-1){const xx=x(p.t),yy=y(p.value);dots+=`M ${xx-4} ${yy} a 4 4 0 1 0 8 0 a 4 4 0 1 0 -8 0 `;}});node('path',{d:dots,class:'dot'});
 const last=points[points.length-1];node('text',{x:x(last.t),y:Math.max(15,y(last.value)-12),'text-anchor':x(last.t)>W/2?'end':'start',class:'end-label'},fmt(last.value,1));
 const cross=node('line',{x1:0,x2:0,y1:T,y2:H-B,class:'crosshair',visibility:'hidden'}),focus=node('circle',{r:5,class:'dot',visibility:'hidden'});
 const tip=el('div',undefined,'tooltip');tip.hidden=true;const valueEl=el('strong'),dateEl=el('p'),nEl=el('p'),sourceEl=el('p');tip.append(valueEl,dateEl,nEl,sourceEl);const live=el('p',undefined,'sr-only');live.setAttribute('aria-live','polite');live.textContent='悬停 / 触摸查看；聚焦图表后用左右方向键逐点阅读。';
 let selected=points.length-1;
 function show(index, announce=false) {
   selected = Math.max(0, Math.min(index, points.length-1));
   const p = points[selected], xx = x(p.t), yy = y(p.value);
   const date = p.first === p.last ? iso(p.first) : iso(p.first)+' — '+iso(p.last);
   cross.setAttribute('x1', xx); cross.setAttribute('x2', xx);
   cross.setAttribute('visibility', 'visible');
   focus.setAttribute('cx', xx); focus.setAttribute('cy', yy);
   focus.setAttribute('visibility', 'visible');
   valueEl.textContent = fmt(p.value, 2)+' '+m.unit;
   dateEl.textContent = date+' · '+(mode === 'day' ? '日值' : p.rows.length+' 个记录日的'+(m.kind === 'min' ? '最低值' : '均值'));
   nEl.textContent = 'n = '+p.n;
   sourceEl.textContent = '来源：'+p.source;
   tip.hidden = false;
   const width = box.clientWidth;
   tip.style.left = Math.max(0, Math.min(xx/W*width+12, width-tip.offsetWidth))+'px';
   tip.style.top = Math.max(0, yy/H*svg.getBoundingClientRect().height-tip.offsetHeight-12)+'px';
   if (announce) live.textContent = [valueEl.textContent, dateEl.textContent, nEl.textContent, sourceEl.textContent].join('；');
 }
 function hide() {
   tip.hidden = true;
   cross.setAttribute('visibility', 'hidden'); focus.setAttribute('visibility', 'hidden');
 }
 svg.addEventListener('pointermove', event => {
   const rect = svg.getBoundingClientRect();
   const target = start+(((event.clientX-rect.left)/rect.width*W-L)/PW)*(end-start);
   let lo = 0, hi = points.length-1;
   while (lo < hi) {
     const mid = Math.floor((lo+hi)/2);
     if (points[mid].t < target) lo = mid+1; else hi = mid;
   }
   if (lo > 0 && Math.abs(points[lo-1].t-target) < Math.abs(points[lo].t-target)) lo--;
   show(lo);
 });
 svg.addEventListener('pointerleave', hide);
 svg.addEventListener('focus', () => show(selected, true));
 svg.addEventListener('blur', hide);
 svg.addEventListener('keydown', event => {
   if (event.key === 'Escape') { hide(); return; }
   const next = event.key === 'ArrowLeft' ? selected-1 : event.key === 'ArrowRight' ? selected+1
     : event.key === 'Home' ? 0 : event.key === 'End' ? points.length-1 : null;
   if (next !== null) { event.preventDefault(); show(next, true); }
 });
 box.append(svg, tip, live);
 return box;
}
const categories = [
  {id:'overview', label:'概览', ids:['sleep','spo2_min','resting_hr','steps','hrv','respiratory']},
  {id:'sleep', label:'睡眠', ids:['sleep','sleep_total','sleep_unspecified','sleep_core','sleep_deep','sleep_rem','sleep_awake','sleep_goal','wrist_temp','breathing_disturbances']},
  {id:'heart', label:'心脏与呼吸', ids:['resting_hr','heart_rate','walking_hr','hr_recovery','hrv','hrv_rmssd','spo2_min','spo2','respiratory']},
  {id:'activity', label:'活动与训练', ids:['steps','exercise','active_energy','basal_energy','distance','vo2','daylight','flights','stand_time','stand_hours','physical_effort','workout_effort','workout_minutes','workout_sessions','mindful']},
  {id:'mobility', label:'步态与移动', ids:['walking_speed','step_length','six_min_walk','stair_ascent','stair_descent','double_support','walking_asymmetry','walking_steadiness']},
  {id:'audio', label:'声音', ids:['environment_audio','headphone_audio','sound_reduction']},
  {id:'body', label:'身体', ids:['weight','height']},
  {id:'coverage', label:'数据覆盖', ids:[]},
];
let activeCategory = 'overview';
let currentRange = null;
function inCategory(m, category) {
  if (category.id === 'body') {
    // Future/optional metrics remain reachable instead of silently disappearing.
    return category.ids.includes(m.id) || !categories.filter(c => !['overview','body','coverage'].includes(c.id)).some(c => c.ids.includes(m.id));
  }
  return category.ids.includes(m.id);
}
function summaryValue(m, rows) {
  // Exclude the export's potentially partial last day from cumulative headline means.
  // The plot and table still expose that day's original value.
  const cumulative = m.kind === 'sum' && !String(m.id || '').startsWith('sleep');
  const summaryRows = cumulative ? rows.filter(r => r.t !== fullEnd) : rows;
  const value = m.kind === 'min'
    ? (summaryRows.length ? summaryRows.reduce((v, r) => Math.min(v, r.value), Infinity) : null)
    : mean(summaryRows);
  const label = m.kind === 'min' ? '所选期间最低采样' : m.id === 'sleep' ? '主睡眠实睡 · 有记录日均值' : '有记录日均值';
  return {value, label, count:summaryRows.length, excludesLast:summaryRows.length !== rows.length};
}
function drawTabs(slices) {
  $('tabs').replaceChildren();
  categories.forEach((category, index) => {
    const button = el('button', category.label);
    button.type = 'button'; button.id = 'tab-'+category.id;
    button.setAttribute('role', 'tab'); button.setAttribute('aria-controls', 'charts');
    button.setAttribute('aria-selected', String(activeCategory === category.id));
    button.tabIndex = activeCategory === category.id ? 0 : -1;
    const count = category.id === 'coverage' ? slices.length : slices.filter(s => inCategory(s.m, category)).length;
    button.append(el('span', count, 'tab-count'));
    button.onclick = () => {
      activeCategory = category.id;
      if (currentRange) render(...currentRange);
      $('tab-'+category.id).focus();
    };
    button.onkeydown = event => {
      const next = event.key === 'ArrowRight' ? (index+1)%categories.length
        : event.key === 'ArrowLeft' ? (index+categories.length-1)%categories.length
        : event.key === 'Home' ? 0 : event.key === 'End' ? categories.length-1 : null;
      if (next !== null) { event.preventDefault(); $('tab-'+categories[next].id).click(); }
    };
    $('tabs').append(button);
  });
  $('charts').setAttribute('aria-labelledby', 'tab-'+activeCategory);
}
function renderCoverage(slices, days) {
  const panel = el('section', undefined, 'coverage-panel');
  const available = slices.filter(s => s.rows.length).length;
  panel.append(el('h2', '当前筛选 · '+available+' / '+slices.length+' 项指标有日值'));
  panel.append(el('p', '日覆盖＝有有效日值的天数 / 当前区间日历天数；不是佩戴时长，也不是临床覆盖率。', 'chart-note'));
  const link = el('a', '查看完整导出清单、未分析类型与选定来源（固定范围）');
  link.href = '#methodology';
  link.onclick = () => { $('methodology').open = true; };
  panel.append(link);
  const scroll = el('div', undefined, 'table-scroll'), table = el('table', undefined, 'coverage-table');
  const head = el('thead'), header = el('tr'), body = el('tbody');
  ['指标', '有记录日 / 区间天数', '日覆盖', '首末日', '本区间实际来源'].forEach(label => {
    const th = el('th', label); th.scope = 'col'; header.append(th);
  });
  head.append(header);
  for (const {m, rows} of slices) {
    const row = el('tr');
    [m.label, rows.length+' / '+days, fmt(rows.length/days*100, 1)+'%',
      rows.length ? rows[0].date+' — '+rows[rows.length-1].date : '无记录',
      rows.length ? sources(rows) : '无记录'].forEach(value => row.append(el('td', value)));
    body.append(row);
  }
  table.append(head, body); scroll.append(table); panel.append(scroll); $('charts').append(panel);
}
function metricCard(m, rows, start, end, days) {
  const card = el('article', undefined, 'card'+(rows.length ? '' : ' no-data'));
  const head = el('div', undefined, 'card-head');
  head.append(el('h3', m.label), el('span', rows.length ? rows.length+' 天有记录' : '暂无记录', 'unit'));
  card.append(head);
  if (!rows.length) {
    card.append(el('p', '此范围无有效日值，缺失不等于零。', 'empty'));
    return card;
  }
  const summary = summaryValue(m, rows), value = el('div', fmt(summary.value, m.id === 'steps' ? 0 : 1), 'metric-number');
  value.append(el('small', m.unit));
  card.append(value, el('p', summary.label+(summary.excludesLast ? ' · 不含导出末日' : '')+' · '+sourceLabel(sources(rows)), 'metric-context'));
  card.append(chart(rows, m, start, end));
  const details = el('details', undefined, 'metric-details');
  const resolution = days > 730 ? '月' : days > 180 ? '周' : '日';
  details.append(el('summary', resolution+'视图 · '+(m.kind === 'min' ? '最低值' : resolution === '日' ? '原始日值' : '记录日均值')+' · 口径与日表'));
  const definition = m.id === 'sleep' ? '最长主睡眠会话的实睡时长，不是全天睡眠总量。'
    : m.kind === 'sum' ? '日值为当日累计；有记录不代表完整佩戴。'
    : m.kind === 'min' ? '每日最低离散采样，不是持续低氧时长；周／月分段也保留最低值。'
    : m.kind === 'median' ? '日值为当日样本中位数，标题数值为这些日值的均值。' : '日值口径沿用上游定义。';
  details.append(el('p', definition, 'chart-note'));
  if (m.note) details.append(el('p', m.note, 'chart-note'));
  details.append(el('p', rows.length+' / '+days+' 天有记录（'+fmt(rows.length/days*100, 1)+'%） · n = '+nsum(rows)+' · 首 '+rows[0].date+' / 末 '+rows[rows.length-1].date, 'chart-note'));
  details.append(el('p', '来源：'+sources(rows)+'。缺失日不补零、不插值；周／月遇缺失日切断分段。纵轴自适应，不是健康阈值。', 'chart-note'));
  if (summary.excludesLast) details.append(el('p', '导出末日可能不完整：均值排除该日，图表与日表保留其记录。其余日期也不保证全天佩戴。', 'chart-note'));
  details.append(tableView(rows, m)); card.append(details);
  return card;
}
function render(start, end) {
  currentRange = [start, end];
  const days = Math.round((end-start)/DAY)+1;
  $('filter-status').classList.remove('error');
  $('filter-status').textContent = '当前筛选 '+iso(start)+' — '+iso(end)+' · '+days+' 天 · 快捷范围以导出结束日 '+iso(fullEnd)+' 为锚点，非今天';
  $('kpis').replaceChildren(); $('charts').replaceChildren();
  const selectedSource = $('source-filter').value;
  const slices = metrics.map(m => {
    const sourceRows = selectedSource === 'default' ? m.rows : (m.series[selectedSource] || []);
    return {m, rows:sourceRows.filter(r => r.t >= start && r.t <= end)};
  });
  // Fixed identities prevent summary tiles from jumping when a range has no data.
  for (const id of ['sleep','spo2_min','resting_hr','steps']) {
    const slice = slices.find(s => s.m.id === id);
    const m = slice ? slice.m : {id, label:defaults[id] || '每日最低血氧', unit:'', kind:id === 'spo2_min' ? 'min' : id === 'steps' ? 'sum' : 'median'};
    const rows = slice ? slice.rows : [], summary = summaryValue(m, rows);
    const tile = el('article', undefined, 'kpi'), label = el('div', undefined, 'kpi-label');
    label.append(el('span', undefined, 'metric-key'), el('span', m.label));
    const value = el('div', fmt(summary.value, id === 'steps' ? 0 : 1), 'kpi-value');
    value.append(el('small', m.unit));
    tile.append(label, value, el('p', rows.length ? summary.label+(summary.excludesLast ? ' · 不含末日' : '') : '当前范围无有效记录'));
    $('kpis').append(tile);
  }
  drawTabs(slices);
  if (activeCategory === 'coverage') { renderCoverage(slices, days); return; }
  const category = categories.find(c => c.id === activeCategory);
  let shown = slices.filter(s => inCategory(s.m, category));
  if (activeCategory === 'overview') {
    shown.sort((a, b) => category.ids.indexOf(a.m.id)-category.ids.indexOf(b.m.id));
  }
  for (const {m, rows} of shown) $('charts').append(metricCard(m, rows, start, end, days));
  if (!shown.length) $('charts').append(el('p', '该分类未提供指标。请查看数据覆盖或切换分类。', 'empty'));
}
function apply() {
  if (!validBounds) {
    $('filter-status').textContent = '缺少有效报告日期；请提供 meta.start / meta.end 或有效日记录。';
    return;
  }
  let start = fullStart, end = fullEnd;
  const range = $('range').value;
  if (range === 'custom') {
    start = day($('start').value); end = day($('end').value);
    if (start === null || end === null || start > end) {
      $('filter-status').textContent = '请输入有效日期，起始不得晚于结束；下方保留上次有效范围。';
      $('filter-status').classList.add('error');
      return;
    }
  } else if (range === 'focus') {
    start = Math.min(end, Math.max(fullStart, day(meta.focus_start) ?? end-29*DAY));
  } else if (range !== 'all') {
    start = end-(Number(range)-1)*DAY;
  }
  // Native date controls always receive normalized ISO dates, never locale strings.
  $('start').value = iso(start); $('end').value = iso(end);
  render(start, end);
}
if (!validBounds) $('range').disabled = true;
$('range').addEventListener('change', () => {
  const custom = $('range').value === 'custom';
  $('custom').hidden = !custom;
  if (!custom) apply();
});
$('source-filter').addEventListener('change', apply);
$('filters').addEventListener('submit', event => { event.preventDefault(); apply(); });
apply();
})();
</script>
</body>
</html>
'''


def main() -> None:
    """Read normalized JSON and write a self-contained HTML file."""
    parser = argparse.ArgumentParser(description="Render an offline health report from normalized JSON")
    parser.add_argument("input", type=Path, help="Normalized JSON input")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Destination HTML file")
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    args.output.write_text(render_report(data), encoding="utf-8")


if __name__ == "__main__":
    main()
