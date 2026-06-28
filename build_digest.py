# -*- coding: utf-8 -*-
"""
ビジネスニュース・デイリーダイジェスト レンダラ（決定的）
usage: python3 build_digest.py day_data.json [output_dir]

役割分担:
  日次HTML digest_<date>.html = ①連動フロー図 ②時事ニュース ③企業分析 ④今後起きそうなこと
  index.html (ダッシュボード)   = 業界の動き(2026) ＋ 掘り下げライブラリ(累積) ＋ 日次一覧

永続ストア（output_dir 内, gitで追跡）:
  trends.json     … 最新の「業界の動き(2026)」スナップショット（毎回上書き）
  deepdives.json  … 掘り下げの累積ライブラリ（トピック重複は排除して追記）

day_data.json schema:
{
 "date_label":"2026年6月27日（金）","date_iso":"2026-06-27",
 "flow":{"nodes":{"D1":[col,y,"sent","l1","l2"],...},"edges":[["D1","S1","mix","label"],...]},
 "trends":[["名称","#color","説明"],...],
 "news":[{"ind":,"head":,"url":,"bg":,"summ":,"points":[..],"forecast":,"study":[..],"pos":,"neg":},...],
 "companies":[["名","コード","業種","時価総額","本日の動き","ポジ/区切り","ネガ/区切り"],...],
 "preds":[["事象","確度","関連企業"],...],
 "deeps":[["トピック","説明","関連","【用語】解説 【用語2】解説"],...]
}
"""
import html, json, sys, glob, os, re

IND_COLOR = {
 "金融":"#2563eb","通信・政策":"#0891b2","通信":"#0891b2","通信・EC":"#0891b2","自動車":"#7c3aed",
 "エネルギー":"#059669","AI":"#db2777","AI(米・非上場)":"#db2777","金融政策":"#2563eb","製薬・市場":"#16a34a",
 "広告・AI":"#db2777","広告":"#db2777","マーケット":"#475569","半導体":"#ea580c","半導体(海外)":"#ea580c",
 "海外金融政策":"#2563eb","地政学":"#b91c1c","海外マクロ":"#b45309","製薬M&A":"#16a34a","製薬/バイオ":"#16a34a",
 "エンタメ":"#7c3aed","ゲーム":"#7c3aed","IT・投資":"#db2777","投資・通信":"#db2777","マクロ":"#475569",
 "半導体装置":"#ea580c","防衛":"#334155","銀行":"#2563eb",
}
def icolor(ind): return IND_COLOR.get(ind, IND_COLOR.get(ind.split("(")[0], "#475569"))
def esc(s): return html.escape(str(s))

CSS = '''
 *{box-sizing:border-box} body{margin:0;background:#f1f5f9;color:#0f172a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Hiragino Sans','Noto Sans JP',sans-serif;line-height:1.65}
 .wrap{max-width:1340px;margin:0 auto;padding:28px 20px 70px} .eyebrow{color:#64748b;font-size:13px;font-weight:700;letter-spacing:1px}
 h1{font-size:26px;margin:4px 0 2px} .sub{color:#64748b;font-size:14px} .home{font-size:12.5px;margin-top:4px} .home a{color:#2563eb;text-decoration:none}
 .toc{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px} .toc a{font-size:12.5px;text-decoration:none;color:#334155;background:#fff;border:1px solid #e2e8f0;border-radius:20px;padding:5px 13px}
 .toc a:hover{border-color:#94a3b8} section{background:white;border:1px solid #e2e8f0;border-radius:16px;padding:22px;margin-top:22px;box-shadow:0 1px 2px rgba(15,23,42,.04);scroll-margin-top:14px}
 h2{font-size:18px;margin:0 0 4px;display:flex;align-items:center;gap:9px} h2 .num{display:inline-flex;width:24px;height:24px;border-radius:7px;background:#0f172a;color:#fff;font-size:13px;align-items:center;justify-content:center}
 .lead{color:#64748b;font-size:13.5px;margin:0 0 16px} .diagram{overflow-x:auto;border:1px solid #eef2f7;border-radius:12px;background:#fcfdfe;padding:10px}
 .legend{display:flex;flex-wrap:wrap;gap:16px;margin-top:14px;font-size:12.5px;color:#475569} .lg{display:inline-flex;align-items:center;gap:6px}
 .sw{width:22px;border-top:3px solid;display:inline-block;border-radius:2px} .dot{width:11px;height:11px;border-radius:3px;display:inline-block}
 .note{margin-top:14px;font-size:12.5px;color:#475569;background:#f8fafc;border-left:3px solid #cbd5e1;padding:10px 12px;border-radius:8px}
 .tgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:13px} .tcard{border:1px solid #e8edf3;border-radius:11px;padding:13px 15px;background:#fbfcfe}
 .tname{font-weight:800;font-size:14px;margin-bottom:4px} .tdesc{font-size:12.5px;color:#475569}
 details.news,details.deep{border:1px solid #e8edf3;border-radius:11px;margin-bottom:10px;background:#fff;overflow:hidden} details.news[open]{box-shadow:0 3px 12px rgba(15,23,42,.07)}
 details.news summary{list-style:none;cursor:pointer;padding:13px 15px;display:flex;flex-wrap:wrap;align-items:center;gap:9px} details.news summary::-webkit-details-marker,details.deep summary::-webkit-details-marker{display:none}
 .ind{font-size:11px;font-weight:700;padding:2px 9px;border-radius:20px;white-space:nowrap} .nhead{font-weight:700;font-size:14.5px;flex:1 1 320px}
 .pnsmall{font-size:11.5px;color:#64748b;flex:1 1 100%} .pnsmall .p{color:#16a34a} .pnsmall .n{color:#dc2626;margin-left:8px}
 .ndetail{padding:4px 16px 16px;border-top:1px dashed #eef2f7} .block{margin-top:11px} .block h4{margin:0 0 3px;font-size:12px;color:#0891b2;letter-spacing:.5px}
 .block p{margin:0;font-size:13px;color:#334155} .block ul{margin:4px 0;padding-left:18px;font-size:13px;color:#334155} .block li{margin:2px 0}
 .chips{display:flex;flex-wrap:wrap;gap:6px} .chip{font-size:11px;background:#f1f5f9;border:1px solid #e2e8f0;border-radius:6px;padding:2px 8px;color:#475569}
 .src{display:inline-block;margin-top:12px;font-size:12px;color:#2563eb;text-decoration:none}
 .cgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:13px} .ccard{border:1px solid #e8edf3;border-radius:12px;padding:14px 15px;background:#fff}
 .chead{display:flex;align-items:baseline;gap:8px} .cname{font-weight:800;font-size:15px} .ccode{font-size:11.5px;color:#94a3b8}
 .cmeta{display:flex;gap:10px;font-size:11.5px;color:#64748b;margin:3px 0 8px} .cind{font-weight:700;color:#475569}
 .csumm{font-size:12.5px;color:#334155;margin:0 0 10px} .cpn{display:flex;flex-wrap:wrap;gap:5px;align-items:center;margin-top:5px}
 .lab{font-size:10.5px;font-weight:800;padding:2px 7px;border-radius:5px} .pl{background:#f0fdf4;color:#16a34a} .nl{background:#fef2f2;color:#dc2626}
 .pc{font-size:11px;background:#f0fdf4;color:#166534;border-radius:6px;padding:2px 7px} .nc{font-size:11px;background:#fef2f2;color:#991b1b;border-radius:6px;padding:2px 7px}
 .pred{border:1px solid #e8edf3;border-left:4px solid #cbd5e1;border-radius:10px;padding:11px 14px;margin-bottom:9px;background:#fff}
 .conf{font-size:10.5px;font-weight:700;padding:2px 9px;border-radius:20px;float:right} .pwhat{font-size:13.5px;font-weight:600;color:#1e293b} .pcomp{font-size:11.5px;color:#64748b;margin-top:3px}
 details.deep summary{cursor:pointer;padding:13px 15px;font-weight:700;font-size:14.5px;list-style:none;display:flex;align-items:center;gap:9px}
 .dtopic::before{content:"🔎 "} .ddate{font-size:11px;color:#94a3b8;font-weight:600;margin-left:auto}
 .ddetail{padding:2px 16px 16px;border-top:1px dashed #eef2f7} .ddetail p{font-size:13px;color:#334155} .dcomp{font-size:11.5px;color:#64748b;margin:6px 0} .ddetail h4{font-size:12px;color:#0891b2;margin:10px 0 4px}
 ul.terms{padding-left:0;list-style:none;margin:0} ul.terms li{font-size:12.5px;color:#334155;background:#f8fafc;border-radius:8px;padding:8px 11px;margin-bottom:6px}
 a.item{display:flex;justify-content:space-between;align-items:center;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:14px 18px;margin-bottom:9px;text-decoration:none;color:#0f172a}
 a.item:hover{border-color:#94a3b8;box-shadow:0 3px 10px rgba(15,23,42,.06)} a.item .d{font-weight:700} a.item .arw{color:#2563eb;font-size:13px}
 footer{color:#94a3b8;font-size:12px;margin-top:26px;text-align:center}
'''

# ---------- flow diagram ----------
COLW={1:215,2:230,3:200,4:215}; COLX={1:24,2:362,3:728,4:1052}; HH=64
SENT={'pos':{'bar':'#16a34a','tag':'ポジ','bg':'#f0fdf4'},'neg':{'bar':'#dc2626','tag':'ネガ','bg':'#fef2f2'},
 'mix':{'bar':'#d97706','tag':'混在','bg':'#fffbeb'},'drv':{'bar':'#475569','tag':'起点','bg':'#f8fafc'}}
EKIND={'pos':'#16a34a','neg':'#dc2626','mix':'#94a3b8','ease':'#0891b2'}
def build_svg(flow):
    NODES=flow["nodes"]; EDGES=flow["edges"]
    def anc(nid):
        col,y,_,_,_=NODES[nid]; x=COLX[col]; w=COLW[col]; return (x,x+w,y+HH/2)
    def nbox(nid):
        col,y,sent,l1,l2=NODES[nid]; x=COLX[col]; w=COLW[col]; s=SENT[sent]; o=[]
        o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{HH}" rx="10" fill="white" stroke="#e2e8f0" stroke-width="1.5"/>')
        o.append(f'<rect x="{x}" y="{y}" width="6" height="{HH}" rx="3" fill="{s["bar"]}"/>')
        o.append(f'<rect x="{x+w-46}" y="{y+8}" width="38" height="16" rx="8" fill="{s["bg"]}" stroke="{s["bar"]}" stroke-width="1"/>')
        o.append(f'<text x="{x+w-27}" y="{y+20}" font-size="10.5" fill="{s["bar"]}" text-anchor="middle" font-weight="700">{esc(s["tag"])}</text>')
        o.append(f'<text x="{x+16}" y="{y+28}" font-size="13.5" fill="#0f172a" font-weight="700">{esc(l1)}</text>')
        o.append(f'<text x="{x+16}" y="{y+48}" font-size="11" fill="#64748b">{esc(l2)}</text>')
        return "\n".join(o)
    def epath(f,t,k,label,i):
        _,frx,fy=anc(f); tlx,_,ty=anc(t); x1,y1=frx,fy; x2,y2=tlx,ty; dx=x2-x1
        c1x=x1+dx*0.45; c2x=x2-dx*0.45; color=EKIND[k]; dash='' if k!='ease' else ' stroke-dasharray="5 4"'
        p=f'<path d="M {x1} {y1} C {c1x} {y1} {c2x} {y2} {x2} {y2}" fill="none" stroke="{color}" stroke-width="2.2"{dash} marker-end="url(#ah_{k})" opacity="0.92"/>'
        lx=x1+dx*0.5; ly=(y1+y2)/2-2+(-10 if i%2==0 else 10); wpx=len(label)*7.2+12
        lab=(f'<rect x="{lx-wpx/2:.1f}" y="{ly-11:.1f}" width="{wpx:.1f}" height="17" rx="8" fill="white" stroke="{color}" stroke-width="1" opacity="0.96"/>'
             f'<text x="{lx:.1f}" y="{ly+1:.1f}" font-size="10.5" fill="{color}" text-anchor="middle" font-weight="600">{esc(label)}</text>')
        return p,lab
    VH=int(max(v[1] for v in NODES.values())+HH+40)
    P=[f'<svg viewBox="0 0 1290 {VH}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;min-width:980px" font-family="-apple-system,\'Hiragino Sans\',\'Noto Sans JP\',sans-serif">','<defs>']
    for k,c in EKIND.items():
        P.append(f'<marker id="ah_{k}" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 Z" fill="{c}"/></marker>')
    P.append('</defs>')
    for col,t in [(1,'起点ドライバー'),(2,'第一次の波及（業界）'),(3,'伝播メカニズム'),(4,'市場・帰結')]:
        P.append(f'<text x="{COLX[col]+COLW[col]/2}" y="24" font-size="12.5" fill="#94a3b8" text-anchor="middle" font-weight="700" letter-spacing="1">{esc(t)}</text>')
    paths=[];labels=[]
    for i,e in enumerate(EDGES):
        p,lab=epath(e[0],e[1],e[2],e[3],i); paths.append(p); labels.append(lab)
    P.extend(paths)
    for nid in NODES: P.append(nbox(nid))
    P.extend(labels); P.append('</svg>'); return "\n".join(P)

LEGEND='''<div class="legend"><span class="lg"><span class="dot" style="background:#475569"></span><b>起点</b></span>
 <span class="lg"><span class="dot" style="background:#16a34a"></span>ポジ</span><span class="lg"><span class="dot" style="background:#dc2626"></span>ネガ</span>
 <span class="lg"><span class="dot" style="background:#d97706"></span>混在</span><span class="lg"><span class="sw" style="border-color:#16a34a"></span>プラス波及</span>
 <span class="lg"><span class="sw" style="border-color:#dc2626"></span>マイナス波及</span><span class="lg"><span class="sw" style="border-color:#0891b2;border-top-style:dashed"></span>緩和要因</span></div>'''

def deep_terms_html(terms):
    parts=re.split(r'(?=【)',terms); return "".join(f"<li>{esc(p.strip())}</li>" for p in parts if p.strip())

# ---------- daily ----------
def render_daily(d):
    news=d["news"]; comps=d["companies"]; preds=d["preds"]
    SVG=build_svg(d["flow"]); DL=d["date_label"]
    nitems=[]
    for n in news:
        c=icolor(n["ind"]); bl="".join(f"<li>{esc(b)}</li>" for b in n.get("points",[]))
        ch="".join(f'<span class="chip">{esc(s)}</span>' for s in n.get("study",[]))
        nitems.append(f'''<details class="news"><summary>
   <span class="ind" style="background:{c}1a;color:{c};border:1px solid {c}55">{esc(n["ind"])}</span>
   <span class="nhead">{esc(n["head"])}</span>
   <span class="pnsmall"><b class="p">＋</b>{esc(n.get("pos",""))}　<b class="n">−</b>{esc(n.get("neg",""))}</span></summary>
 <div class="ndetail">
   <div class="block"><h4>背景</h4><p>{esc(n.get("bg",""))}</p></div>
   <div class="block"><h4>サマリ</h4><p>{esc(n.get("summ",""))}</p></div>
   <div class="block"><h4>重要ポイント</h4><ul>{bl}</ul></div>
   <div class="block"><h4>今後の予測</h4><p>{esc(n.get("forecast",""))}</p></div>
   <div class="block"><h4>勉強テーマ</h4><div class="chips">{ch}</div></div>
   {f'<a class="src" href="{esc(n["url"])}" target="_blank" rel="noopener">出典リンク ↗</a>' if n.get("url") else ''}
 </div></details>''')
    ccards=[]
    for name,code,ind,cap,summ,pos,neg in comps:
        pc="".join(f'<span class="pc">{esc(x.strip())}</span>' for x in pos.split("/") if x.strip())
        nc="".join(f'<span class="nc">{esc(x.strip())}</span>' for x in neg.split("/") if x.strip())
        ccards.append(f'''<div class="ccard"><div class="chead"><span class="cname">{esc(name)}</span><span class="ccode">{esc(code)}</span></div>
  <div class="cmeta"><span class="cind">{esc(ind)}</span><span class="ccap">時価総額 {esc(cap)}</span></div>
  <p class="csumm">{esc(summ)}</p>
  <div class="cpn"><span class="lab pl">ポジ</span>{pc}</div>
  <div class="cpn"><span class="lab nl">ネガ</span>{nc}</div></div>''')
    cc={"高":"#dc2626","中":"#d97706","低":"#64748b"}
    prows="".join(f'''<div class="pred"><span class="conf" style="background:{cc.get(cf.strip(),"#64748b")}1a;color:{cc.get(cf.strip(),"#64748b")};border:1px solid {cc.get(cf.strip(),"#64748b")}66">確度 {esc(cf)}</span>
  <div class="pwhat">{esc(w)}</div><div class="pcomp">関連: {esc(cm)}</div></div>''' for w,cf,cm in preds)
    return f'''<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ビジネスニュース・デイリーダイジェスト {esc(DL)}</title><style>{CSS}</style></head><body><div class="wrap">
 <header><div class="eyebrow">BUSINESS NEWS — DAILY DIGEST</div><h1>ビジネスニュース・デイリーダイジェスト</h1>
   <div class="sub">{esc(DL)} ／ 国内中心＋主要海外　|　全{len(news)}トピック・企業{len(comps)}社・予測{len(preds)}件</div>
   <div class="home"><a href="./index.html">← ダッシュボード（業界の動き・掘り下げライブラリ・過去一覧）へ</a></div>
   <nav class="toc"><a href="#map">① 連動マップ</a><a href="#news">② 時事ニュース</a><a href="#company">③ 企業分析</a><a href="#pred">④ 今後起きそうなこと</a></nav></header>
 <section id="map"><h2><span class="num">1</span>業界連動マップ（因果フロー）</h2>
   <p class="lead">きょうの主要トピックの因果連鎖。色＝影響の符号、矢印＝波及の向き。業界横断のマクロ文脈は<a href="./index.html#trend">ダッシュボードの「業界の動き(2026)」</a>を参照。</p>
   <div class="diagram">{SVG}</div>{LEGEND}</section>
 <section id="news"><h2><span class="num">2</span>時事ニュース（全項目）</h2><p class="lead">見出しをクリックで、背景・サマリ・重要ポイント・今後の予測・勉強テーマを表示。</p>{"".join(nitems)}</section>
 <section id="company"><h2><span class="num">3</span>企業分析（本日動いた企業）</h2><p class="lead">その日の主役企業の財務スナップショット＋ポジ/ネガ＋直近の動き。</p><div class="cgrid">{"".join(ccards)}</div></section>
 <section id="pred"><h2><span class="num">4</span>今後起きそうなこと</h2><p class="lead">その日のニュースから論理的に予測できる中短期の展開（確度つき）。</p>{prows}</section>
 <footer>生成: Cowork デイリーダイジェスト ／ {esc(DL)}　|　深掘りトピックは<a href="./index.html#deep">ライブラリ</a>に蓄積</footer></div></body></html>'''

# ---------- index dashboard ----------
def render_index(outdir):
    trends=[]; deeps=[]; master=None
    tp=os.path.join(outdir,"trends.json"); dp=os.path.join(outdir,"deepdives.json"); mp=os.path.join(outdir,"masterflow.json")
    if os.path.exists(tp): trends=json.load(open(tp,encoding="utf-8"))
    if os.path.exists(dp): deeps=json.load(open(dp,encoding="utf-8"))
    if os.path.exists(mp): master=json.load(open(mp,encoding="utf-8"))
    master_section=""
    if master and master.get("nodes"):
        master_section=f'''<section id="master"><h2><span class="num">0</span>全体連動マップ（全分野・累積アップデート）</h2>
   <p class="lead">これまでのニュースを踏まえた、全分野横断の構造マップ。日次ニュースで関係が変わるたびに更新します（その日だけの因果図は各日次の冒頭に掲載）。色＝影響の符号、矢印＝波及の向き。</p>
   <div class="diagram">{build_svg(master)}</div>{LEGEND}</section>'''
    tcards="".join(f'<div class="tcard" style="border-top:3px solid {c}"><div class="tname" style="color:{c}">{esc(n)}</div><div class="tdesc">{esc(t)}</div></div>' for n,c,t in trends)
    # deepdives newest first
    dcards=[]
    for e in deeps:
        topic,desc,comp,terms=e[0],e[1],e[2],e[3]; date=e[4] if len(e)>4 else ""
        dcards.append(f'''<details class="deep"><summary><span class="dtopic">{esc(topic)}</span><span class="ddate">{esc(date)}</span></summary>
  <div class="ddetail"><p>{esc(desc)}</p><div class="dcomp">関連: {esc(comp)}</div>
    <h4>キーワード・構造解説</h4><ul class="terms">{deep_terms_html(terms)}</ul></div></details>''')
    files=sorted(glob.glob(os.path.join(outdir,"digest_*.html")), reverse=True)
    items=[]
    for f in files:
        b=os.path.basename(f); m=re.search(r'digest_(\d{4}-\d{2}-\d{2})\.html',b)
        if not m: continue
        items.append(f'<a class="item" href="./{b}"><span class="d">{m.group(1)}</span><span class="arw">日次ダイジェストを開く →</span></a>')
    latest=f'<div class="home"><a href="./{os.path.basename(files[0])}">→ 最新の日次ダイジェストを開く</a></div>' if files else ''
    body=f'''<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ビジネスニュース・ダイジェスト ダッシュボード</title><style>{CSS}</style></head><body><div class="wrap">
 <header><div class="eyebrow">BUSINESS NEWS — DASHBOARD</div><h1>ビジネスニュース・ダッシュボード</h1>
   <div class="sub">業界の動き（2026年）・掘り下げライブラリ（累積）・日次ダイジェスト一覧</div>{latest}
   <nav class="toc"><a href="#master">全体連動マップ</a><a href="#trend">業界の動き(2026)</a><a href="#deep">掘り下げライブラリ</a><a href="#list">日次一覧</a></nav></header>
 {master_section}
 <section id="trend"><h2><span class="num">A</span>業界の動き（2026年）</h2><p class="lead">日次ニュースを読むための、業界別マクロ文脈（随時更新）。</p><div class="tgrid">{tcards}</div></section>
 <section id="deep"><h2><span class="num">B</span>掘り下げ・分析ライブラリ（累積 {len(deeps)}件）</h2><p class="lead">業界構造・投資テーマ・用語の解説を日々蓄積。新しい順。</p>{"".join(dcards)}</section>
 <section id="list"><h2><span class="num">C</span>日次ダイジェスト一覧</h2><p class="lead">毎晩自動生成。新しい順。</p>{"".join(items)}</section>
 <footer>Cowork ビジネスニュース・ダッシュボード</footer></div></body></html>'''
    open(os.path.join(outdir,"index.html"),"w",encoding="utf-8").write(body)
    return len(items),len(deeps),len(trends)

def update_stores(d,outdir):
    # masterflow.json: 全体連動マップ（毎回上書き更新）
    if d.get("masterflow") and d["masterflow"].get("nodes"):
        json.dump(d["masterflow"],open(os.path.join(outdir,"masterflow.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=1)
    # trends.json: overwrite with latest snapshot
    if d.get("trends"):
        json.dump(d["trends"],open(os.path.join(outdir,"trends.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=1)
    # deepdives.json: append new (dedupe by topic), newest first
    dp=os.path.join(outdir,"deepdives.json")
    lib=json.load(open(dp,encoding="utf-8")) if os.path.exists(dp) else []
    existing={e[0] for e in lib}
    added=0
    for e in d.get("deeps",[]):
        if e[0] in existing: continue
        lib.insert(0, [e[0],e[1],e[2],e[3], d.get("date_iso","")])
        existing.add(e[0]); added+=1
    json.dump(lib,open(dp,"w",encoding="utf-8"),ensure_ascii=False,indent=1)
    return added

if __name__=="__main__":
    data=json.load(open(sys.argv[1],encoding="utf-8"))
    outdir=sys.argv[2] if len(sys.argv)>2 else "."
    iso=data["date_iso"]
    out=os.path.join(outdir,f"digest_{iso}.html")
    open(out,"w",encoding="utf-8").write(render_daily(data))
    added=update_stores(data,outdir)
    n,nd,nt=render_index(outdir)
    print(f"wrote {out} | index: {n} digests, deepdive-library {nd} (+{added} new), trends {nt}")
