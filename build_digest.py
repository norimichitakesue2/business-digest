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
 "半導体装置":"#ea580c","防衛":"#334155","銀行":"#2563eb","製薬":"#16a34a","商社":"#0d9488",
 "不動産":"#9333ea","小売・消費":"#e11d48","素材・化学":"#b45309","建設":"#78716c","運輸・物流":"#0891b2",
}
def icolor(ind): return IND_COLOR.get(ind, IND_COLOR.get(ind.split("(")[0], "#475569"))
def esc(s): return html.escape(str(s))
def _wrap_cjk(s, max_chars, max_lines):
    """日本語テキストを文字数でword-wrap。max_lines超過分は末尾…で省略。"""
    s=str(s).strip(); lines=[]
    while s:
        if len(lines)==max_lines-1 and len(s)>max_chars:
            lines.append(s[:max(1,max_chars-1)]+"…"); s=""; break
        lines.append(s[:max_chars]); s=s[max_chars:]
        if len(lines)>=max_lines: break
    return lines or [""]

CSS = '''
 *{box-sizing:border-box} body{margin:0;background:#f1f5f9;color:#0f172a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Hiragino Sans','Noto Sans JP',sans-serif;line-height:1.65}
 .wrap{max-width:1340px;margin:0 auto;padding:28px 20px 70px} .eyebrow{color:#64748b;font-size:13px;font-weight:700;letter-spacing:1px}
 h1{font-size:26px;margin:4px 0 2px} .sub{color:#64748b;font-size:14px} .home{font-size:12.5px;margin-top:4px} .home a{color:#2563eb;text-decoration:none}
 .toc{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px} .toc a{font-size:12.5px;text-decoration:none;color:#334155;background:#fff;border:1px solid #e2e8f0;border-radius:20px;padding:5px 13px}
 .toc a:hover{border-color:#94a3b8} section{background:white;border:1px solid #e2e8f0;border-radius:16px;padding:22px;margin-top:22px;box-shadow:0 1px 2px rgba(15,23,42,.04);scroll-margin-top:14px}
 h2{font-size:18px;margin:0 0 4px;display:flex;align-items:center;gap:9px} h2 .num{display:inline-flex;width:24px;height:24px;border-radius:7px;background:#0f172a;color:#fff;font-size:13px;align-items:center;justify-content:center}
 .lead{color:#64748b;font-size:13.5px;margin:0 0 16px} .diagram{overflow-x:auto;border:1px solid #eef2f7;border-radius:12px;background:#fcfdfe;padding:10px;-webkit-overflow-scrolling:touch}
 @media (max-width:700px){.diagram::before{content:"← 図は横にスクロールできます →";display:block;position:sticky;left:0;font-size:11px;color:#94a3b8;text-align:center;margin-bottom:6px}}
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
# ノード⇄ニュースの業界タグ辞書（部分一致でタグ付け→共通タグがあれば関連付け）
TAGMAP={
 'semi':['半導体','SOX','キオクシア','メモリ'],'ai':['AI','LLM','データセンター','ソブリン'],
 'fin':['銀行','メガバンク','金融','日銀','利上げ','利ざや','為替介入'],
 'energy':['エネルギー','原油','石油','ガス','Brent','ホルムズ'],'power':['電力','重電','再エネ','核融合','送配電'],
 'auto':['自動車','ＥＶ','EV','トヨタ','VW','電池','HEV'],'retail':['小売','消費','百貨店','インバウンド','資産効果'],
 'food':['食品','値上げ','外食','ナフサ'],'reit':['不動産','REIT','ＲＥＩＴ'],
 'pharma':['製薬','薬品','ヘルスケア','武田','第一三共','創薬'],'defense':['防衛','宇宙','護衛艦','SpaceX'],
 'telecom':['通信','携帯','楽天','京浜急行','京急','ARPU'],'trading':['商社','素材','三菱商事','三井物産'],
 'construction':['建設','ゼネコン','竹中','WLC'],'hr':['人材','求人','賃上げ','雇用'],
 'ent':['エンタメ','任天堂','ソニー','ＩＰ'],'market':['マーケット','日経平均','ドル円','ユーロ円','クロス円','株式相場','株価','日経'],
 'china':['中国'],'us':['米国','FRB','S&P','Warsh','ナスダック'],'trade':['通商','関税','輸出','供給網','対米投資'],
}
def _btags(text):
    return {tag for tag,subs in TAGMAP.items() if any(s in text for s in subs)}
def _bmatch(l1,l2,news):
    if not news: return []
    nt=_btags(l1+" "+l2)
    if not nt: return []
    out=[]
    for n in news:
        if _btags(n.get("ind","")+" "+n.get("head","")) & nt:
            out.append({"ind":n.get("ind",""),"head":n.get("head",""),"summ":n.get("summ",""),"url":n.get("url","")})
    return out[:5]
def build_svg(flow, news=None, idbase=0, node_news=None, node_meta=None):
    NODES=flow["nodes"]; EDGES=flow["edges"]; pops=[]
    def anc(nid):
        col,y=NODES[nid][0],NODES[nid][1]; x=COLX[col]; w=COLW[col]; return (x,x+w,y+HH/2)
    def nbox(nid):
        col,y,sent,l1,l2=NODES[nid][:5]; x=COLX[col]; w=COLW[col]; s=SENT[sent]; o=[]
        tcpl=max(6,int((w-66)/13.0)); scpl=max(8,int((w-26)/10.6))
        tl=_wrap_cjk(l1,tcpl,2); sl=_wrap_cjk(l2,scpl,1)[0] if l2 else ""
        o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{HH}" rx="10" fill="white" stroke="#e2e8f0" stroke-width="1.5"/>')
        o.append(f'<rect x="{x}" y="{y}" width="6" height="{HH}" rx="3" fill="{s["bar"]}"/>')
        o.append(f'<rect x="{x+w-46}" y="{y+8}" width="38" height="16" rx="8" fill="{s["bg"]}" stroke="{s["bar"]}" stroke-width="1"/>')
        o.append(f'<text x="{x+w-27}" y="{y+20}" font-size="10.5" fill="{s["bar"]}" text-anchor="middle" font-weight="700">{esc(s["tag"])}</text>')
        if len(tl)==1:
            o.append(f'<text x="{x+16}" y="{y+27}" font-size="13.5" fill="#0f172a" font-weight="700">{esc(tl[0])}</text>')
            if sl: o.append(f'<text x="{x+16}" y="{y+47}" font-size="11" fill="#64748b">{esc(sl)}</text>')
        else:
            o.append(f'<text x="{x+16}" y="{y+21}" font-size="13.5" fill="#0f172a" font-weight="700">{esc(tl[0])}</text>')
            o.append(f'<text x="{x+16}" y="{y+38}" font-size="13.5" fill="#0f172a" font-weight="700">{esc(tl[1])}</text>')
            if sl: o.append(f'<text x="{x+16}" y="{y+55}" font-size="10.5" fill="#64748b">{esc(sl)}</text>')
        extra=NODES[nid][5] if len(NODES[nid])>5 else None
        nw=node_news.get(nid) if (node_news and nid in node_news) else _bmatch(l1,l2,news)
        mrec=(node_meta.get(nid,{}) if node_meta else {})
        comps=mrec.get("companies")
        desc=mrec.get("desc"); why=mrec.get("why")
        # 関連性（つながり）をエッジから自動生成：入ってくる影響(上流)と出ていく影響(下流)
        ins=[{"n":NODES[e[0]][3],"k":e[2],"l":(e[3] if len(e)>3 else "")} for e in EDGES if e[1]==nid and e[0] in NODES]
        outs=[{"n":NODES[e[1]][3],"k":e[2],"l":(e[3] if len(e)>3 else "")} for e in EDGES if e[0]==nid and e[1] in NODES]
        idx=idbase+len(pops); pops.append({"t":l1,"s":l2,"tag":s["tag"],"color":s["bar"],"sent":sent,
            "news":nw,"extra":extra,"desc":desc,"why":why,"ins":ins,"outs":outs,"companies":comps})
        o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{HH}" rx="10" fill="transparent"/>')
        return f'<g class="fnode" style="cursor:pointer" onclick="bnShowPop({idx})">'+"\n".join(o)+'</g>'
    def _col(nid): return NODES[nid][0]
    def _gutter_r(c):
        rc=COLX[c]+COLW[c]
        return (rc+COLX[c+1])/2 if (c+1) in COLX else rc+42
    def _gutter_l(c):
        return (COLX[c-1]+COLW[c-1]+COLX[c])/2 if (c-1) in COLX else COLX[c]-42
    def epath(f,t,k,label,i):
        cf=_col(f); ct=_col(t); color=EKIND[k]; dash='' if k!='ease' else ' stroke-dasharray="5 4"'
        fl,fr,fy=anc(f); tl,tr,ty=anc(t)
        if ct>cf:  # 前進（左→右）：ラベルは源泉列の右側ガターへ
            x1,y1=fr,fy; x2,y2=tl,ty; dx=x2-x1; c1x=x1+dx*0.45; c2x=x2-dx*0.45
            p=f'<path d="M {x1} {y1} C {c1x} {y1} {c2x} {y2} {x2} {y2}" fill="none" stroke="{color}" stroke-width="2.2"{dash} marker-end="url(#ah_{k})" opacity="0.9"/>'
            lx=_gutter_r(cf); ly=y1+(y2-y1)*0.14+(-9 if i%2==0 else 9)
        elif cf==ct:  # 同一列（縦）：ガターへ迂回。末尾列は左、それ以外は右
            if (cf+1) in COLX: gx=_gutter_r(cf); x1,y1=fr,fy; x2,y2=tr,ty
            else: gx=_gutter_l(cf); x1,y1=fl,fy; x2,y2=tl,ty
            p=f'<path d="M {x1} {y1} C {gx} {y1} {gx} {y2} {x2} {y2}" fill="none" stroke="{color}" stroke-width="2"{dash} marker-end="url(#ah_{k})" opacity="0.85"/>'
            lx=gx; ly=(y1+y2)/2+(-9 if i%2==0 else 9)
        else:  # 後退（右→左）フォールバック：源泉列の左ガターへ
            gx=_gutter_l(cf); x1,y1=fl,fy; x2,y2=tr,ty
            p=f'<path d="M {x1} {y1} C {gx} {y1} {gx} {y2} {x2} {y2}" fill="none" stroke="{color}" stroke-width="2"{dash} marker-end="url(#ah_{k})" opacity="0.85"/>'
            lx=gx; ly=(y1+y2)/2+(-9 if i%2==0 else 9)
        wpx=len(label)*7.2+12
        lab=(f'<rect x="{lx-wpx/2:.1f}" y="{ly-11:.1f}" width="{wpx:.1f}" height="17" rx="8" fill="white" stroke="{color}" stroke-width="1" opacity="0.97"/>'
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
    P.extend(labels); P.append('</svg>'); return "\n".join(P), pops

LEGEND='''<div class="legend"><span class="lg"><span class="dot" style="background:#475569"></span><b>起点</b></span>
 <span class="lg"><span class="dot" style="background:#16a34a"></span>ポジ</span><span class="lg"><span class="dot" style="background:#dc2626"></span>ネガ</span>
 <span class="lg"><span class="dot" style="background:#d97706"></span>混在</span><span class="lg"><span class="sw" style="border-color:#16a34a"></span>プラス波及</span>
 <span class="lg"><span class="sw" style="border-color:#dc2626"></span>マイナス波及</span><span class="lg"><span class="sw" style="border-color:#0891b2;border-top-style:dashed"></span>緩和要因</span></div>'''

def deep_terms_html(terms):
    parts=re.split(r'(?=【)',terms); return "".join(f"<li>{esc(p.strip())}</li>" for p in parts if p.strip())

# ---------- node tap → popup ----------
MODAL_CSS='''
.bnov{position:fixed;inset:0;background:rgba(15,23,42,.45);opacity:0;pointer-events:none;transition:.15s;z-index:60}
.bnov.on{opacity:1;pointer-events:auto}
.bnpop{position:fixed;left:50%;top:50%;transform:translate(-50%,-46%) scale(.98);width:min(560px,92vw);max-height:82vh;overflow:auto;background:#fff;border-radius:16px;box-shadow:0 24px 60px rgba(15,23,42,.3);padding:20px 20px 22px;opacity:0;pointer-events:none;transition:.16s;z-index:61}
.bnpop.on{opacity:1;pointer-events:auto;transform:translate(-50%,-50%) scale(1)}
.bnx{position:absolute;top:12px;right:14px;border:none;background:#f1f5f9;width:30px;height:30px;border-radius:50%;font-size:18px;line-height:1;color:#475569;cursor:pointer}
.bnhd{display:flex;align-items:center;gap:9px;flex-wrap:wrap;padding-right:34px}
.bntag{font-size:11px;font-weight:700;padding:2px 9px;border-radius:8px;border:1px solid}
.bnt{font-size:16px;font-weight:800;color:#0f172a}
.bns{color:#64748b;font-size:13px;margin:6px 0 14px}
.bnnh{font-size:12px;font-weight:700;color:#94a3b8;letter-spacing:.5px;margin:0 0 8px}
.bnn{border:1px solid #e8edf3;border-radius:11px;padding:11px 13px;margin-bottom:9px;background:#fcfdfe}
.bnni{display:inline-block;font-size:11px;font-weight:700;color:#2563eb;margin-bottom:4px}
.bnnh2{font-size:13.5px;font-weight:700;color:#0f172a;line-height:1.45}
.bnns{font-size:12.5px;color:#475569;margin-top:5px;line-height:1.5}
.bnnl{display:inline-block;margin-top:7px;font-size:12px;color:#2563eb;text-decoration:none}
.bnempty{font-size:13px;color:#64748b;line-height:1.6}
.bnextra{font-size:12.5px;color:#334155;line-height:1.6;background:#f8fafc;border-left:3px solid #cbd5e1;border-radius:8px;padding:9px 12px;margin:0 0 14px}
.bnsec{margin:0 0 14px}
.bndesc{font-size:13px;color:#0f172a;line-height:1.62;background:#f8fafc;border-left:3px solid #cbd5e1;border-radius:8px;padding:9px 12px}
.bnwhy{display:flex;align-items:flex-start;gap:8px;flex-wrap:wrap}
.bnsb{font-size:11px;font-weight:700;padding:2px 9px;border-radius:8px;border:1px solid;white-space:nowrap}
.bnwt{font-size:12.5px;color:#334155;line-height:1.55;flex:1;min-width:60%}
.bnrelh{font-size:11.5px;font-weight:700;color:#64748b;margin:9px 0 4px}
.bnrel{display:flex;align-items:center;gap:8px;padding:5px 0;border-top:1px dashed #eef2f7}
.bnkb{font-size:10.5px;font-weight:700;padding:1px 7px;border-radius:7px;border:1px solid;white-space:nowrap}
.bnrn{font-size:12.5px;font-weight:600;color:#0f172a}
.bnrl{font-size:11.5px;color:#64748b;margin-left:auto;text-align:right;max-width:52%}
.bncos{display:flex;flex-direction:column;gap:6px;margin-bottom:14px}
.bnco{display:flex;align-items:baseline;gap:8px;border:1px solid #e8edf3;border-radius:9px;padding:7px 11px;background:#fcfdfe}
.bncon{font-size:13px;font-weight:700;color:#0f172a;white-space:nowrap}
.bncor{font-size:11.5px;color:#64748b;line-height:1.4}
.fnode:hover rect:first-child{stroke:#94a3b8;stroke-width:2}
'''
BN_MODAL='''<div id="bnov" class="bnov" onclick="bnClose()"></div>
<div id="bnpop" class="bnpop" role="dialog" aria-modal="true">
 <button class="bnx" onclick="bnClose()" aria-label="閉じる">×</button>
 <div class="bnhd"><span id="bntag" class="bntag"></span><span id="bnt" class="bnt"></span></div>
 <div id="bns" class="bns"></div><div id="bnbody"></div></div>'''
def bn_script(pops):
    js='''<script>
window.__BNPOPS__=%s;
function bnE(s){return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function bnClose(){document.getElementById('bnov').classList.remove('on');document.getElementById('bnpop').classList.remove('on');}
function bnShowPop(i){var p=window.__BNPOPS__[i];if(!p)return;
 document.getElementById('bnt').textContent=p.t;
 var tag=document.getElementById('bntag');tag.textContent=p.tag;tag.style.color=p.color;tag.style.borderColor=p.color;tag.style.background=p.color+'1a';
 document.getElementById('bns').textContent=p.s||'';
 var b=document.getElementById('bnbody');var h='';
 var SENTM={pos:{t:'ポジ（追い風）',c:'#16a34a'},neg:{t:'ネガ（逆風）',c:'#dc2626'},mix:{t:'混在（両面）',c:'#d97706'},drv:{t:'起点（ドライバー）',c:'#475569'}};
 var KINDM={pos:{t:'促進',c:'#16a34a'},neg:{t:'抑制',c:'#dc2626'},mix:{t:'中立',c:'#94a3b8'},ease:{t:'緩和',c:'#0891b2'}};
 function kbadge(k){var m=KINDM[k]||{t:k,c:'#94a3b8'};return '<span class="bnkb" style="color:'+m.c+';border-color:'+m.c+';background:'+m.c+'22">'+m.t+'</span>';}
 // 解説（何のノードか）
 if(p.desc){h+='<div class="bnsec"><div class="bnnh">解説</div><div class="bndesc">'+bnE(p.desc)+'</div></div>';}
 else if(p.extra){h+='<div class="bnextra">'+bnE(p.extra)+'</div>';}
 // 位置づけ（ポジ／ネガの理由）
 if(p.sent){var sm=SENTM[p.sent]||{t:p.sent,c:'#475569'};
  h+='<div class="bnsec"><div class="bnnh">位置づけ（'+(p.sent==='drv'?'なぜ起点か':'ポジ／ネガの理由')+'）</div><div class="bnwhy"><span class="bnsb" style="color:'+sm.c+';border-color:'+sm.c+';background:'+sm.c+'1a">'+sm.t+'</span>'+(p.why?'<span class="bnwt">'+bnE(p.why)+'</span>':'')+'</div></div>';}
 // つながり（関連ノードとの関係）
 if((p.ins&&p.ins.length)||(p.outs&&p.outs.length)){
  h+='<div class="bnsec"><div class="bnnh">このノードのつながり</div>';
  if(p.ins&&p.ins.length){h+='<div class="bnrelh">← 上流から（このノードが受ける影響）</div>';
   p.ins.forEach(function(r){h+='<div class="bnrel">'+kbadge(r.k)+'<span class="bnrn">'+bnE(r.n)+'</span>'+(r.l?'<span class="bnrl">'+bnE(r.l)+'</span>':'')+'</div>';});}
  if(p.outs&&p.outs.length){h+='<div class="bnrelh">→ 下流へ（このノードが与える影響）</div>';
   p.outs.forEach(function(r){h+='<div class="bnrel">'+kbadge(r.k)+'<span class="bnrn">'+bnE(r.n)+'</span>'+(r.l?'<span class="bnrl">'+bnE(r.l)+'</span>':'')+'</div>';});}
  h+='</div>';}
 if(p.companies&&p.companies.length){h+='<div class="bnnh">関連企業（'+p.companies.length+'社）</div><div class="bncos">';
  p.companies.forEach(function(c){var nm=Array.isArray(c)?c[0]:c;var ro=Array.isArray(c)?(c[1]||''):'';
   h+='<div class="bnco"><span class="bncon">'+bnE(nm)+'</span>'+(ro?'<span class="bncor">'+bnE(ro)+'</span>':'')+'</div>';});
  h+='</div>';}
 if(p.news&&p.news.length){h+='<div class="bnnh">関連ニュース（'+p.news.length+'件）</div>';
  p.news.forEach(function(n){h+='<div class="bnn"><div class="bnni">'+bnE(n.ind)+'</div><div class="bnnh2">'+bnE(n.head)+'</div>'+(n.summ?'<div class="bnns">'+bnE(n.summ)+'</div>':'')+(n.url?'<a class="bnnl" href="'+encodeURI(n.url)+'" target="_blank" rel="noopener">出典リンク ↗</a>':'')+'</div>';});
 }else{h+='<div class="bnempty">このノードに直接ひも付くニュースは見つかりませんでした。日次ダイジェストの「時事ニュース」もご覧ください。</div>';}
 b.innerHTML=h;
 document.getElementById('bnov').classList.add('on');document.getElementById('bnpop').classList.add('on');}
document.addEventListener('keydown',function(e){if(e.key==='Escape')bnClose();});
</script>'''
    return js % json.dumps(pops,ensure_ascii=False)

# ---------- daily ----------
def render_daily(d):
    news=d.get("news",[]); comps=d.get("companies",[]); preds=d.get("preds",[]); DL=d["date_label"]
    has_flow=bool(d.get("flow") and d["flow"].get("nodes"))
    backfill=d.get("backfill",False)
    nitems=[]
    for n in news:
        c=icolor(n["ind"]); bl="".join(f"<li>{esc(b)}</li>" for b in n.get("points",[]))
        ch="".join(f'<span class="chip">{esc(s)}</span>' for s in n.get("study",[]))
        pn=""
        if n.get("pos") or n.get("neg"):
            pn=f'<span class="pnsmall"><b class="p">＋</b>{esc(n.get("pos",""))}　<b class="n">−</b>{esc(n.get("neg",""))}</span>'
        blocks=f'<div class="block"><h4>背景</h4><p>{esc(n.get("bg",""))}</p></div>' if n.get("bg") else ""
        blocks+=f'<div class="block"><h4>サマリ</h4><p>{esc(n.get("summ",""))}</p></div>' if n.get("summ") else ""
        blocks+=f'<div class="block"><h4>重要ポイント</h4><ul>{bl}</ul></div>' if bl else ""
        blocks+=f'<div class="block"><h4>今後の予測</h4><p>{esc(n.get("forecast",""))}</p></div>' if n.get("forecast") else ""
        blocks+=f'<div class="block"><h4>勉強テーマ</h4><div class="chips">{ch}</div></div>' if ch else ""
        src=f'<a class="src" href="{esc(n["url"])}" target="_blank" rel="noopener">出典リンク ↗</a>' if n.get("url") else ''
        nitems.append(f'''<details class="news"><summary>
   <span class="ind" style="background:{c}1a;color:{c};border:1px solid {c}55">{esc(n["ind"])}</span>
   <span class="nhead">{esc(n["head"])}</span>{pn}</summary>
 <div class="ndetail">{blocks}{src}</div></details>''')
    # optional sections
    secs=[]; toc=[]; num=1; flow_pops=[]
    if has_flow:
        _svg,flow_pops=build_svg(d["flow"], news)
        toc.append('<a href="#map">① 連動マップ</a>')
        secs.append(f'''<section id="map"><h2><span class="num">{num}</span>業界連動マップ（因果フロー）</h2>
   <p class="lead">きょうの主要トピックの因果連鎖。色＝影響の符号、矢印＝波及の向き。<b>各ノードをタップすると関連ニュースをポップアップ表示</b>します。業界横断のマクロ文脈は<a href="./index.html#trend">ダッシュボードの「業界の動き(2026)」</a>を参照。</p>
   <div class="diagram">{_svg}</div>{LEGEND}</section>'''); num+=1
    toc.append(f'<a href="#news">時事ニュース</a>')
    secs.append(f'''<section id="news"><h2><span class="num">{num}</span>時事ニュース（全項目）</h2><p class="lead">見出しをクリックで、背景・サマリ・重要ポイント・今後の予測・勉強テーマを表示。{'（過去データのバックフィル版。フロー図・ポジ/ネガは当時未記録のため省略）' if backfill else ''}</p>{"".join(nitems)}</section>'''); num+=1
    if comps:
        ccards=[]
        for name,code,ind,cap,summ,pos,neg in comps:
            pc="".join(f'<span class="pc">{esc(x.strip())}</span>' for x in pos.split("/") if x.strip())
            nc="".join(f'<span class="nc">{esc(x.strip())}</span>' for x in neg.split("/") if x.strip())
            ccards.append(f'''<div class="ccard"><div class="chead"><span class="cname">{esc(name)}</span><span class="ccode">{esc(code)}</span></div>
  <div class="cmeta"><span class="cind">{esc(ind)}</span><span class="ccap">時価総額 {esc(cap)}</span></div>
  <p class="csumm">{esc(summ)}</p>
  <div class="cpn"><span class="lab pl">ポジ</span>{pc}</div>
  <div class="cpn"><span class="lab nl">ネガ</span>{nc}</div></div>''')
        toc.append('<a href="#company">企業分析</a>')
        secs.append(f'''<section id="company"><h2><span class="num">{num}</span>企業分析（本日動いた企業）</h2><p class="lead">その日の主役企業の財務スナップショット＋ポジ/ネガ＋直近の動き。</p><div class="cgrid">{"".join(ccards)}</div></section>'''); num+=1
    if preds:
        cc={"高":"#dc2626","中":"#d97706","低":"#64748b"}
        def _prow(p):
            w=p[0]; cf=p[1] if len(p)>1 else "中"; cm=p[2] if len(p)>2 else ""
            hz=p[3] if len(p)>3 and p[3] else pred_horizon(w)
            col=cc.get(cf.strip(),"#64748b")
            hzt=f'・{esc(hz)}' if hz else ''
            return f'''<div class="pred"><span class="conf" style="background:{col}1a;color:{col};border:1px solid {col}66">確度 {esc(cf)}{hzt}</span>
  <div class="pwhat">{esc(w)}</div><div class="pcomp">関連: {esc(cm)}</div></div>'''
        prows="".join(_prow(p) for p in preds)
        toc.append('<a href="#pred">今後起きそうなこと</a>')
        secs.append(f'''<section id="pred"><h2><span class="num">{num}</span>今後起きそうなこと</h2><p class="lead">その日のニュースから論理的に予測できる中短期の展開（確度つき）。</p>{prows}</section>'''); num+=1
    cnt=f'全{len(news)}トピック'+(f'・企業{len(comps)}社' if comps else '')+(f'・予測{len(preds)}件' if preds else '')
    return f'''<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ビジネスニュース・デイリーダイジェスト {esc(DL)}</title><style>{CSS}{MODAL_CSS}</style></head><body><div class="wrap">
 <header><div class="eyebrow">BUSINESS NEWS — DAILY DIGEST</div><h1>ビジネスニュース・デイリーダイジェスト</h1>
   <div class="sub">{esc(DL)} ／ 国内中心＋主要海外　|　{cnt}</div>
   <div class="home"><a href="./index.html">← ダッシュボード（業界の動き・掘り下げライブラリ・過去一覧）へ</a></div>
   <nav class="toc">{"".join(toc)}</nav></header>
 {"".join(secs)}
 <footer>生成: Cowork デイリーダイジェスト ／ {esc(DL)}　|　深掘りトピックは<a href="./index.html#deep">ライブラリ</a>に蓄積</footer></div>{BN_MODAL}{bn_script(flow_pops)}</body></html>'''

# ---------- index dashboard ----------
def render_index(outdir):
    trends=[]; deeps=[]; master=None
    tp=os.path.join(outdir,"trends.json"); dp=os.path.join(outdir,"deepdives.json"); mp=os.path.join(outdir,"masterflow.json")
    if os.path.exists(tp): trends=json.load(open(tp,encoding="utf-8"))
    if os.path.exists(dp): deeps=json.load(open(dp,encoding="utf-8"))
    if os.path.exists(mp): master=json.load(open(mp,encoding="utf-8"))
    cpath=os.path.join(outdir,"companies.json"); ppath=os.path.join(outdir,"predictions.json")
    ncomp=len(json.load(open(cpath,encoding="utf-8"))) if os.path.exists(cpath) else 0
    npred=len(json.load(open(ppath,encoding="utf-8"))) if os.path.exists(ppath) else 0
    _sg_cards,_sg_n,_sg_d=_story_cards_html(outdir)
    navcards=f'''<section id="lib"><h2><span class="num">◎</span>ライブラリ</h2><p class="lead">詳しい分析は別ページに集約しています。</p>
   <div class="navcards">
     <a class="navcard" href="./sectors.html"><div class="nt">🗺 業界構造マップ</div><div class="nd">分野別のバリューチェーン（上流→下流）と主要企業の結びつき。ノードから関連ニュースへ。</div><div class="na">構造マップを見る →</div></a>
     <a class="navcard" href="./companies.html"><div class="nt">🏢 企業分析ライブラリ</div><div class="nd">登場企業を集約。売上高・PER・PBR・ROE・時価総額＋今後の期待。並べ替え可。</div><div class="na">全{ncomp}社を見る →</div></a>
     <a class="navcard" href="./predictions.html"><div class="nt">🔮 今後の予測マップ</div><div class="nd">「今後起きそうなこと」を確度×時間軸でマッピング。累積一覧つき。</div><div class="na">全{npred}件を見る →</div></a>
     <a class="navcard" href="./deepdives.html"><div class="nt">🔎 掘り下げ：問いで追う論点</div><div class="nd">日々の掘り下げを「問い」ごとに束ね、いまの見立てと論点の推移を時系列で。検索つき。</div><div class="na">{_sg_n}本の問いを見る →</div></a>
     <a class="navcard" href="./updates.html"><div class="nt">🗓 更新ログ</div><div class="nd">毎日のダイジェストで何が追加・変化したか（業界の潮目・構造マップ・掘り下げ・予測）。</div><div class="na">日付順に追う →</div></a>
   </div></section>'''
    npath=os.path.join(outdir,"news.json")
    news_store=json.load(open(npath,encoding="utf-8")) if os.path.exists(npath) else []
    master_section=""; master_pops=[]
    if master and master.get("nodes"):
        _msvg,master_pops=build_svg(master, news_store[:160])
        master_section=f'''<section id="master"><h2><span class="num">1</span>いまの全体像（2026年）</h2>
   <p class="lead">最新のニュースまでを反映した「いまの業界地図」です。毎日上書きで更新され、常に最新版だけを表示します（その日だけの因果図は各日次の冒頭に掲載）。</p>
   <div class="subh">① 業界どうしのつながり（全体連動マップ）</div>
   <p class="lead">色＝影響の符号、矢印＝波及の向き。<b>各ノードをタップすると詳細を表示</b>します。</p>
   <div class="diagram">{_msvg}</div>{LEGEND}
   <div class="subh" id="trend">② 業界ごとの見立て</div>
   <p class="lead">大分類ごとの2026年の文脈と、含まれる業界の判定（追い風／逆風）。業界名をタップすると業界構造マップの詳細へ移動します。</p>
   <div class="ovwrap">{_overview_cards(outdir, trends)}</div></section>'''
    tcards="".join(f'<div class="tcard" style="border-top:3px solid {c}"><div class="tname" style="color:{c}">{esc(n)}</div><div class="tdesc">{esc(t)}</div></div>' for n,c,t in trends)
    # deepdives newest first
    dcards=[]
    for e in []:
        topic,desc,comp,terms=e[0],e[1],e[2],e[3]; date=e[4] if len(e)>4 else ""
        dcards.append(f'''<details class="deep"><summary><span class="dtopic">{esc(topic)}</span><span class="ddate">{esc(date)}</span></summary>
  <div class="ddetail"><p>{esc(desc)}</p><div class="dcomp">関連: {esc(comp)}</div>
    <h4>キーワード・構造解説</h4><ul class="terms">{deep_terms_html(terms)}</ul></div></details>''')
    files=sorted(glob.glob(os.path.join(outdir,"digest_*.html")), reverse=True)
    items=[]
    # 各日のトップ見出し・件数（news.jsonは日内が逆順で積まれるため、最後に出現したものがその日の先頭記事）
    _np=os.path.join(outdir,"news.json")
    _nl=json.load(open(_np,encoding="utf-8")) if os.path.exists(_np) else []
    _top={}; _cnt={}
    for n in _nl:
        dt=n.get("date","")
        if dt: _top[dt]=n.get("head",""); _cnt[dt]=_cnt.get(dt,0)+1
    _wd="月火水木金土日"
    import datetime as _dtm
    bymonth={}
    for f in files:
        b=os.path.basename(f); m=re.search(r'digest_(\d{4}-\d{2}-\d{2})\.html',b)
        if not m: continue
        iso=m.group(1)
        try: w="（"+_wd[_dtm.date.fromisoformat(iso).weekday()]+"）"
        except Exception: w=""
        hd=_top.get(iso,""); c=_cnt.get(iso,0)
        items.append(iso)
        bymonth.setdefault(iso[:7],[]).append(f'<a class="ditem" href="./{b}"><span class="dd">{int(iso[5:7])}/{int(iso[8:])}<small>{w}</small></span><span class="dh">{esc(hd) if hd else "日次ダイジェスト"}</span><span class="dn">{str(c)+"本" if c else ""}</span><span class="arw">→</span></a>')
    dlist="".join(f'<details class="dmonth"{" open" if i==0 else ""}><summary>{ym[:4]}年{int(ym[5:])}月<span class="dmc">{len(v)}日分</span></summary>{"".join(v)}</details>' for i,(ym,v) in enumerate(bymonth.items()))
    latest=f'<div class="home"><a href="./{os.path.basename(files[0])}">→ 最新の日次ダイジェストを開く</a></div>' if files else ''
    # 月次まとめ
    mfiles=sorted(glob.glob(os.path.join(outdir,"month-*.html")), reverse=True)
    mitems=[]
    for f in mfiles:
        b=os.path.basename(f); mm=re.search(r'month-(\d{4})-(\d{2})\.html',b)
        if not mm: continue
        mitems.append(f'<a class="item" href="./{b}"><span class="d">{mm.group(1)}年{int(mm.group(2))}月まとめ</span><span class="arw">月次まとめを開く →</span></a>')
    month_block=(f'<section id="month"><h2><span class="num">C</span>月次まとめ</h2><p class="lead">その月の主要ストーリーを集約。</p>{"".join(mitems)}</section>') if mitems else ''
    body=f'''<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ビジネスニュース・ダイジェスト ダッシュボード</title><style>{CSS}{MODAL_CSS}{NAV_CSS}{DLIST_CSS}{SUM_CSS}{OV_CSS}{STORY_CSS}{UPD_CSS}</style></head><body><div class="wrap">
 <header><div class="eyebrow">BUSINESS NEWS — DASHBOARD</div><h1>ビジネスニュース・ダッシュボード</h1>
   <div class="sub">今日の変化・いまの全体像（2026年）・問いで追う掘り下げ・日次ダイジェスト一覧</div>{latest}
   <nav class="toc"><a href="#today">今日の変化</a><a href="#master">いまの全体像</a><a href="./sectors.html">業界構造マップ</a><a href="#deep">掘り下げ（問い）</a><a href="./updates.html">更新ログ</a><a href="./companies.html">企業分析</a><a href="./predictions.html">今後の予測</a>{'<a href="#month">月次まとめ</a>' if month_block else ''}<a href="#list">日次一覧</a></nav></header>
 {_today_box(outdir)}
 {master_section}
 <section id="deep"><h2><span class="num">2</span>掘り下げ：問いで追う論点（{_sg_n}本・累積{len(deeps)}件）</h2><p class="lead">日々の掘り下げを「問い」ごとに束ねています。最近更新された問いが先頭です。カードをタップすると、いまの見立てと論点の推移を表示します。</p><div class="stgrid">{_sg_cards}</div><div class="home" style="margin-top:12px"><a href="./deepdives.html">→ 検索・全件はこちら</a></div></section>
 {navcards}
 {month_block}
 <section id="list"><h2><span class="num">D</span>日次ダイジェスト一覧（全{len(items)}日）</h2><p class="lead">毎晩自動生成。新しい順。各日のトップ記事の見出しを表示しています。月をクリックすると開閉します。</p>{dlist}</section>
 <footer>Cowork ビジネスニュース・ダッシュボード</footer></div>{BN_MODAL}{bn_script(master_pops)}</body></html>'''
    open(os.path.join(outdir,"index.html"),"w",encoding="utf-8").write(body)
    return len(items),len(deeps),len(trends)

# ---------- company / prediction stores + pages ----------
CANON={
 "キオクシアHD":"キオクシアホールディングス","三菱UFJ FG":"三菱UFJフィナンシャル・グループ",
 "NTT":"日本電信電話(NTT)","ソフトバンクG":"ソフトバンクグループ",
}
def canon(n): return CANON.get(n,n)
def pred_horizon(w):
    if any(k in w for k in ["数年","構造的","あと2年","中長期","恒常","常態化","パテントクリフ","定着すれば"]): return "長期"
    if any(k in w for k in ["7月","9月","今週","介入","監査役会","7/9","9月末","党中央政治局","四半期"]): return "短期"
    return "中期"
def _num(s):
    m=re.search(r'-?\d+(?:\.\d+)?', str(s).replace(",",""))
    if not m: return -1e18
    v=float(m.group()); t=str(s)
    if "兆" in t: v*=10000
    return v

CSS_EXTRA='''
 .disc{font-size:12px;color:#92400e;background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:10px 13px;margin:0 0 16px}
 .ctbl-wrap{overflow-x:auto;border:1px solid #eef2f7;border-radius:12px}
 table.ctbl{border-collapse:collapse;width:100%;min-width:900px;font-size:12.5px}
 table.ctbl th,table.ctbl td{padding:9px 11px;text-align:right;border-bottom:1px solid #eef2f7;white-space:nowrap}
 table.ctbl th{background:#f8fafc;color:#475569;font-size:11.5px;position:sticky;top:0;cursor:pointer;user-select:none}
 table.ctbl th:hover{background:#eef2f7} table.ctbl th.act::after{content:" ▾";color:#2563eb}
 table.ctbl th.asc.act::after{content:" ▴"}
 table.ctbl td.l,table.ctbl th.l{text-align:left} table.ctbl tr:hover td{background:#fcfdfe}
 .cnm{font-weight:700;color:#0f172a} .ccd{font-size:11px;color:#94a3b8;margin-left:5px}
 .itag{font-size:10.5px;font-weight:700;padding:1px 7px;border-radius:6px}
 .col{font-size:12.5px;color:#334155;text-align:left;max-width:280px;white-space:normal}
 .neg{color:#dc2626} .pos{color:#16a34a}
 .pmx{display:grid;grid-template-columns:70px 1fr 1fr 1fr;gap:8px;margin-top:6px}
 .pmx .hc{font-size:11.5px;font-weight:800;color:#475569;display:flex;align-items:center;justify-content:center;background:#f8fafc;border-radius:8px;padding:6px;text-align:center}
 .pmx .rl{font-size:13px;line-height:1.4} .pmx .corner{background:transparent}
 @media (max-width:700px){.pmx{grid-template-columns:52px repeat(3,minmax(230px,1fr));overflow-x:auto;padding-bottom:8px;-webkit-overflow-scrolling:touch} .pmx .rl{font-size:12px} .pmx .rl{position:sticky;left:0;z-index:1}}
 .cell{min-height:74px;border:1px solid #eef2f7;border-radius:10px;padding:8px;background:#fcfdfe;display:flex;flex-direction:column;gap:6px}
 .pchip{font-size:11.5px;line-height:1.4;border-left:4px solid;border-radius:8px;padding:6px 9px;background:#fff;box-shadow:0 1px 2px rgba(15,23,42,.04)}
 .pchip .pc2{display:block;font-size:10.5px;color:#94a3b8;margin-top:3px}
 .parch{border:1px solid #e8edf3;border-radius:10px;margin-bottom:8px;background:#fff;overflow:hidden}
 .parch>summary{list-style:none;cursor:pointer;display:flex;align-items:center;gap:10px;padding:11px 14px;font-weight:800;color:#1e293b;user-select:none}
 .parch>summary::-webkit-details-marker{display:none}
 .parch>summary::after{content:"▸";margin-left:auto;color:#94a3b8;font-size:13px}
 .parch[open]>summary::after{content:"▾"}
 .parch .pth{font-size:13.5px} .parch .pcnt{font-size:11.5px;color:#64748b;background:#f1f5f9;border-radius:20px;padding:2px 10px;font-weight:700}
 .parch .pbody{padding:4px 14px 12px}
 .navcards{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:13px}
 a.navcard{display:block;background:linear-gradient(135deg,#1e293b,#0f172a);color:#fff;border-radius:14px;padding:18px 20px;text-decoration:none}
 a.navcard:hover{box-shadow:0 6px 18px rgba(15,23,42,.18)} a.navcard .nt{font-weight:800;font-size:15px} a.navcard .nd{font-size:12px;color:#cbd5e1;margin-top:4px} a.navcard .na{font-size:12px;color:#93c5fd;margin-top:8px}
'''

NAV_CSS='''
 .navcards{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:13px}
 a.navcard{display:block;background:linear-gradient(135deg,#1e293b,#0f172a);color:#fff;border-radius:14px;padding:18px 20px;text-decoration:none}
 a.navcard:hover{box-shadow:0 6px 18px rgba(15,23,42,.18)} a.navcard .nt{font-weight:800;font-size:15px} a.navcard .nd{font-size:12px;color:#cbd5e1;margin-top:4px} a.navcard .na{font-size:12px;color:#93c5fd;margin-top:8px}
'''
DLIST_CSS='''
 .dmonth{border:1px solid #e2e8f0;border-radius:12px;margin-bottom:10px;background:#fff;overflow:hidden}
 .dmonth>summary{list-style:none;cursor:pointer;padding:12px 16px;font-weight:800;display:flex;align-items:center;gap:10px}
 .dmonth>summary::-webkit-details-marker{display:none} .dmonth>summary::after{content:"▸";margin-left:auto;color:#94a3b8} .dmonth[open]>summary::after{content:"▾"}
 .dmc{font-size:11.5px;color:#64748b;background:#f1f5f9;border-radius:20px;padding:2px 10px;font-weight:700}
 a.ditem{display:flex;align-items:center;gap:12px;padding:10px 16px;border-top:1px solid #eef2f7;text-decoration:none;color:#0f172a}
 a.ditem:hover{background:#f8fafc} .dd{font-weight:800;min-width:62px;font-size:14px} .dd small{font-weight:600;color:#94a3b8;font-size:11px;margin-left:2px}
 .dh{flex:1;font-size:13px;color:#334155;overflow:hidden;text-overflow:ellipsis;white-space:nowrap} .dn{font-size:11.5px;color:#94a3b8;white-space:nowrap} a.ditem .arw{color:#2563eb}
 @media (max-width:640px){.dh{white-space:normal;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical} .dn{display:none}}
'''

def render_companies(outdir):
    cp=os.path.join(outdir,"companies.json")
    comps=json.load(open(cp,encoding="utf-8")) if os.path.exists(cp) else []
    comps=sorted(comps,key=lambda r:(_num(r.get("cap","")))*-1)
    rows=[]
    for r in comps:
        ic=icolor(r.get("ind","")); nm=esc(r.get("name","")); cd=esc(r.get("code",""))
        cap=r.get("cap","—"); rev=r.get("revenue","—"); per=r.get("per","—"); pbr=r.get("pbr","—"); roe=r.get("roe","—")
        outlook=esc(r.get("outlook","") or "—"); ind=esc(r.get("ind",""))
        seen=f'{r.get("first","")}〜{r.get("last","")}'
        roecls=' class="neg"' if str(roe).startswith("-") else ''
        rows.append(f'''<tr>
   <td class="l" data-v="{esc(nm)}"><span class="cnm">{nm}</span><span class="ccd">{cd}</span></td>
   <td class="l" data-v="{ind}"><span class="itag" style="background:{ic}1a;color:{ic}">{ind}</span></td>
   <td data-v="{_num(cap)}">{esc(cap)}</td>
   <td data-v="{_num(rev)}">{esc(rev)}</td>
   <td data-v="{_num(per)}">{esc(per)}</td>
   <td data-v="{_num(pbr)}">{esc(pbr)}</td>
   <td data-v="{_num(roe)}"{roecls}>{esc(roe)}</td>
   <td class="col" data-v="{outlook}">{outlook}</td>
   <td class="l" data-v="{esc(seen)}">{esc(seen)}</td></tr>''')
    heads=[("企業名","l"),("業種","l"),("時価総額",""),("売上高/収益",""),("PER",""),("PBR",""),("ROE",""),("今後の期待","col l"),("登場","l")]
    th="".join(f'<th class="{c}" onclick="csort({i})">{esc(h)}</th>' for i,(h,c) in enumerate(heads))
    disc=('※ 財務数値は各社IR・公開金融情報サイト（IRBANK / Yahoo!ファイナンス / 株探 / みんかぶ 等）を基にした<b>概算・参考値</b>で、取得時点は2026年7月上旬です。市場変動により実値は変わります。最新値は各社IRでご確認ください。'
          '「売上高/収益」は事業により営業収益・売上収益・経常収益（銀行）を含みます。<b>非上場企業（OpenAI・Anthropic 等）はPER/PBR/ROEが存在しないため「—」</b>。キオクシア・ispace等は上場直後や赤字でPBR/ROEが極端値となるため参考値です。時価総額は特記なき場合は円、海外企業はドル/ユーロ/ウォン等の現地通貨表記です。')
    body=f'''<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>企業分析ライブラリ｜ビジネスニュース・ダッシュボード</title><style>{CSS}{CSS_EXTRA}</style></head><body><div class="wrap">
 <header><div class="eyebrow">BUSINESS NEWS — COMPANY LIBRARY</div><h1>企業分析ライブラリ（累積）</h1>
   <div class="sub">これまでの日次ダイジェストに登場した企業を集約。主要財務指標＋今後の期待。全{len(comps)}社</div>
   <div class="home"><a href="./index.html">← ダッシュボードへ戻る</a></div></header>
 <section><h2><span class="num">★</span>企業一覧（{len(comps)}社）</h2>
   <p class="lead">列見出しをクリックで並べ替え。既定は時価総額の大きい順。</p>
   <div class="disc">{disc}</div>
   <div class="ctbl-wrap"><table class="ctbl" id="ct"><thead><tr>{th}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>
 </section>
 <footer>Cowork ビジネスニュース・ダッシュボード ／ 企業分析ライブラリ</footer></div>
<script>
var casc=true,clast=-1;
function csort(i){{var tb=document.querySelector('#ct tbody');var rs=[].slice.call(tb.rows);
 if(i===clast)casc=!casc;else casc=true;clast=i;
 rs.sort(function(a,b){{var x=a.cells[i].getAttribute('data-v'),y=b.cells[i].getAttribute('data-v');
  var nx=parseFloat(x),ny=parseFloat(y);var num=!isNaN(nx)&&!isNaN(ny)&&/^-?\\d/.test(x)&&/^-?\\d/.test(y);
  if(num)return casc?nx-ny:ny-nx;return casc?(''+x).localeCompare(y,'ja'):(''+y).localeCompare(x,'ja');}});
 rs.forEach(function(r){{tb.appendChild(r);}});
 document.querySelectorAll('#ct th').forEach(function(t,j){{t.classList.toggle('act',j===i);t.classList.toggle('asc',j===i&&casc);}});}}
</script></body></html>'''
    open(os.path.join(outdir,"companies.html"),"w",encoding="utf-8").write(body)
    return len(comps)

# テーマ別アーカイブの分類定義（優先順。上から順に最初に当たったテーマへ割当）
PRED_THEMES=[
 ("AI・半導体・データセンター","#7c3aed",["AI","半導体","データセンター","ＤＣ","GPU","NVIDIA","エヌビディア","TSMC","メモリ","DRAM","基板","光ファイバ","クラウド","Compute","計算資源","キオクシア","Arm","OpenAI"]),
 ("金融・金利・為替","#2563eb",["日銀","利上げ","利下げ","金利","為替","円安","円高","ドル円","FRB","銀行","利ざや","国債","TOPIX","メガバンク","住宅ローン","地銀"]),
 ("消費・小売・食品","#ea580c",["値上げ","消費","小売","食品","家計","実質賃金","インバウンド","観光","ビール","PB","販促","スーパー"]),
 ("自動車・製造","#dc2626",["自動車","ＥＶ","EV","HEV","トヨタ","ホンダ","日産","スバル","車載","電池"]),
 ("エネルギー・資源・商社","#b45309",["原油","エネルギー","電力","再エネ","資源","商社","銅","鉄鉱石","LNG","洋上風力","石油"]),
 ("通信・エンタメ","#db2777",["通信","携帯","料金","ARPU","楽天","ドコモ","KDDI","ソフトバンク","エンタメ","ゲーム","任天堂","ソニー","IP","映画","コンテンツ"]),
 ("防衛・宇宙・重工","#475569",["防衛","宇宙","ロケット","衛星","重工","H3","みちびき","測位"]),
 ("製薬・ヘルスケア","#059669",["製薬","医薬","創薬","がん","ヘルスケア","バイオ","エンハーツ","治験","ADC"]),
 ("人材・労働","#4f46e5",["雇用","賃金","人材","労働","求人","採用","ベア","春闘","人手不足"]),
 ("海外・地政学","#334155",["中国","米国","欧州","地政学","関税","輸出管理","台湾","新興国","ECB"]),
]
def _pred_theme(p):
    hay=(p.get("what","")+" "+p.get("comp","")).lower()
    for name,col,kws in PRED_THEMES:
        for kw in kws:
            if kw.lower() in hay: return name,col
    return "その他","#64748b"

def render_predictions(outdir):
    import datetime
    pp=os.path.join(outdir,"predictions.json")
    preds=json.load(open(pp,encoding="utf-8")) if os.path.exists(pp) else []
    cc={"高":"#dc2626","中":"#d97706","低":"#64748b"}
    HZ=["短期","中期","長期"]; CF=["高","中","低"]
    HZLAB={"短期":"短期（〜3カ月）","中期":"中期（〜1年）","長期":"長期（1年〜）"}
    # ---- 直近7日を判定 ----
    dates=[p.get("date","") for p in preds if p.get("date")]
    recent=[]; RWIN=7; CELLCAP=6
    if dates:
        try:
            newest=max(datetime.date.fromisoformat(x) for x in dates)
            thr=newest-datetime.timedelta(days=RWIN)
            recent=[p for p in preds if p.get("date") and datetime.date.fromisoformat(p["date"])>=thr]
        except Exception:
            recent=preds[:24]
    if len(recent)<6: recent=preds[:min(len(preds),18)]  # 日付が薄い場合は直近順で確保
    def chip(p):
        col=cc.get(p.get("conf","中"),"#64748b")
        cm=f'<span class="pc2">関連: {esc(p["comp"])}</span>' if p.get("comp") else ''
        dt=f'<span class="pc2">{esc(p.get("date",""))}</span>' if p.get("date") else ''
        return f'<div class="pchip" style="border-color:{col}">{esc(p["what"])}{cm}{dt}</div>'
    grid=['<div class="pmx"><div class="corner"></div>']
    for h in HZ: grid.append(f'<div class="hc">{esc(HZLAB[h])}</div>')
    for cf in CF:
        grid.append(f'<div class="hc rl" style="color:{cc[cf]}">確度 {esc(cf)}</div>')
        for h in HZ:
            cell=[p for p in recent if p.get("conf")==cf and p.get("horizon",pred_horizon(p["what"]))==h]
            shown=cell[:CELLCAP]
            more=f'<span style="font-size:10.5px;color:#94a3b8;text-align:center">＋他{len(cell)-CELLCAP}件（アーカイブ参照）</span>' if len(cell)>CELLCAP else ''
            grid.append('<div class="cell">'+(("".join(chip(p) for p in shown)+more) if cell else '<span style="color:#cbd5e1;font-size:11px;margin:auto">—</span>')+'</div>')
    grid.append('</div>')
    # ---- テーマ別アーカイブ（折りたたみ・累積） ----
    buckets={}
    for p in preds:
        name,col=_pred_theme(p)
        buckets.setdefault(name,{"col":col,"items":[]})["items"].append(p)
    order=[t[0] for t in PRED_THEMES]+["その他"]
    themed=sorted(buckets.items(), key=lambda kv:(-len(kv[1]["items"]), order.index(kv[0]) if kv[0] in order else 99))
    arch=[]
    for name,info in themed:
        col=info["col"]; items=info["items"]
        rows=[]
        for p in items:
            pcol=cc.get(p.get("conf","中"),"#64748b")
            rows.append(f'''<div class="pred" style="border-left-color:{pcol}">
   <span class="conf" style="background:{pcol}1a;color:{pcol};border:1px solid {pcol}66">確度 {esc(p.get("conf","中"))}・{esc(p.get("horizon",pred_horizon(p["what"])))}</span>
   <div class="pwhat">{esc(p["what"])}</div><div class="pcomp">関連: {esc(p.get("comp","—"))}　<span style="color:#cbd5e1">{esc(p.get("date",""))}</span></div></div>''')
        arch.append(f'''<details class="parch"><summary style="border-left:5px solid {col}"><span class="pth">{esc(name)}</span><span class="pcnt">{len(items)}件</span></summary><div class="pbody">{"".join(rows)}</div></details>''')
    body=f'''<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>今後の予測マップ｜ビジネスニュース・ダッシュボード</title><style>{CSS}{CSS_EXTRA}</style></head><body><div class="wrap">
 <header><div class="eyebrow">BUSINESS NEWS — OUTLOOK MAP</div><h1>今後の予測マップ</h1>
   <div class="sub">日次ダイジェストの「今後起きそうなこと」を集約。直近は確度×時間軸マトリクス、過去はテーマ別に集約（累積{len(preds)}件）</div>
   <div class="home"><a href="./index.html">← ダッシュボードへ戻る</a></div></header>
 <section><h2><span class="num">◇</span>直近1週間の予測（確度 × 時間軸）</h2>
   <p class="lead">縦＝確度（高/中/低）、横＝時間軸（短期〜長期）。右上（高確度×短期）ほど注視度が高い予測です。表示は直近1週間の{len(recent)}件（各セル最大{CELLCAP}件、超過分はテーマ別アーカイブへ）。</p>
   {"".join(grid)}
   <div class="legend"><span class="lg"><span class="dot" style="background:#dc2626"></span>高</span><span class="lg"><span class="dot" style="background:#d97706"></span>中</span><span class="lg"><span class="dot" style="background:#64748b"></span>低</span></div>
 </section>
 <section><h2><span class="num">≡</span>テーマ別アーカイブ（累積{len(preds)}件）</h2><p class="lead">過去の予測をテーマごとに集約しました。見出しをクリックすると展開します。</p>{"".join(arch)}</section>
 <footer>Cowork ビジネスニュース・ダッシュボード ／ 今後の予測マップ</footer></div></body></html>'''
    open(os.path.join(outdir,"predictions.html"),"w",encoding="utf-8").write(body)
    return len(preds)

def _news_for_company(title, aliases, newslist, k=5):
    """企業名（および別名）を見出し・サマリに含むニュースを抽出（新しい順・最大k件）"""
    keys=[a for a in ([title]+list(aliases or [])) if a and len(a)>=2]
    out=[]
    for n in newslist:
        blob=(n.get("head","")+" "+n.get("summ","")+" "+n.get("ind",""))
        if any(kk in blob for kk in keys):
            out.append({"ind":n.get("ind",""),"head":n.get("head",""),"summ":n.get("summ",""),"url":n.get("url","")})
        if len(out)>=k: break
    return out

def render_month(outdir, iso):
    """当月の月次まとめHTMLを自動生成（毎回上書き）。news.json / deepdives.json / digest一覧から集約。"""
    if not iso or len(iso)<7: return None
    ym=iso[:7]; y,m=ym.split("-")
    npath=os.path.join(outdir,"news.json")
    news=json.load(open(npath,encoding="utf-8")) if os.path.exists(npath) else []
    mnews=[n for n in news if str(n.get("date","")).startswith(ym)]
    # 業界別集計
    from collections import Counter, OrderedDict
    cnt=Counter(n.get("ind","その他") for n in mnews)
    days=sorted({n.get("date","") for n in mnews if n.get("date")}, reverse=True)
    # 当月のdigest一覧
    dfiles=sorted(glob.glob(os.path.join(outdir,f"digest_{ym}-*.html")), reverse=True)
    _dpat=re.compile(r"digest_(\d{4}-\d{2}-\d{2})")
    dlink_parts=[]
    for f in dfiles:
        mm=_dpat.search(os.path.basename(f))
        if mm: dlink_parts.append(f'<a class="item" href="./{os.path.basename(f)}"><span class="d">{mm.group(1)}</span><span class="arw">日次を開く →</span></a>')
    dlinks="".join(dlink_parts)
    # 当月の掘り下げ
    dp=os.path.join(outdir,"deepdives.json")
    deeps=json.load(open(dp,encoding="utf-8")) if os.path.exists(dp) else []
    mdeeps=[e for e in deeps if len(e)>4 and str(e[4]).startswith(ym)]
    dcards="".join(f'<details class="deep"><summary><span class="dtopic">{esc(e[0])}</span><span class="ddate">{esc(e[4])}</span></summary><div class="ddetail"><p>{esc(e[1])}</p><div class="dcomp">関連: {esc(e[2])}</div></div></details>' for e in mdeeps)
    # 業界別バー
    total=sum(cnt.values()) or 1; maxc=max(cnt.values()) if cnt else 1
    bars=""
    for ind,c in cnt.most_common():
        col=icolor(ind); w=int(c/maxc*100)
        bars+=f'<div class="mbar"><span class="mbl">{esc(ind)}</span><span class="mbt"><span class="mbf" style="width:{w}%;background:{col}"></span></span><span class="mbn">{c}</span></div>'
    # 主要トピック（各日の先頭ニュース＝その日のトップ）
    byday=OrderedDict()
    for n in mnews:
        dt=n.get("date","")
        if dt not in byday: byday[dt]=None
        byday[dt]=n  # 日内は逆順に積まれるため最後の出現がその日の先頭記事
    tops="".join(f'<div class="mtop"><span class="mtd">{esc(dt)}</span><a href="{esc(t.get("url","#"))}" target="_blank" rel="noopener" class="mth">{esc(t.get("head",""))}</a></div>' for dt,t in list(byday.items())[:16])
    body=f'''<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{y}年{int(m)}月まとめ｜ビジネスニュース・ダッシュボード</title><style>{CSS}{CSS_EXTRA}{MONTH_CSS}</style></head><body><div class="wrap">
 <header><div class="eyebrow">BUSINESS NEWS — MONTHLY</div><h1>{y}年{int(m)}月 マンスリーまとめ</h1>
   <div class="sub">当月に取り上げた {len(mnews)} 本のニュースを集約（{len(days)}営業日・{len(dfiles)}ダイジェスト）。随時更新。</div>
   <div class="home"><a href="./index.html">← ダッシュボードへ戻る</a></div></header>
 <section><h2><span class="num">1</span>今月の主要トピック</h2><p class="lead">各日のトップニュース（新しい順）。</p>{tops or '<p class="lead">データがありません。</p>'}</section>
 <section><h2><span class="num">2</span>業界別のニュース量</h2><p class="lead">当月に多く報じられた分野の分布。</p><div class="mbars">{bars or '—'}</div></section>
 {f'<section><h2><span class="num">3</span>今月追加した掘り下げ（{len(mdeeps)}件）</h2>{dcards}</section>' if mdeeps else ''}
 <section><h2><span class="num">4</span>当月の日次ダイジェスト（{len(dfiles)}件）</h2>{dlinks or '—'}</section>
 <footer>Cowork ビジネスニュース・ダッシュボード ／ {y}年{int(m)}月まとめ</footer></div></body></html>'''
    open(os.path.join(outdir,f"month-{ym}.html"),"w",encoding="utf-8").write(body)
    return ym

def merge_sectors_delta(data, outdir):
    """day_data.json の任意フィールド sectors_delta を sectors.json に加算マージ（増える方向のみ）。
    形式:
      sectors_delta = {
        "new_sectors":[ {key,name,color,lead,flow:{nodes,edges},meta} ],
        "add_nodes":{ "<key>": {"<nid>":[col,y,sent,title,note]} },
        "add_edges":{ "<key>": [[from,to,kind,label]] },
        "add_meta": { "<key>": {"<nid>":{"companies":[[name,role]],"aliases":[..]}} }
      }
    既存ノード/エッジ/セクターは重複追加しない。meta の companies/aliases は和集合で拡張。
    戻り値: (追加セクター数, 追加ノード数, 追加エッジ数)。sectors_delta 未指定なら (0,0,0)。"""
    delta=data.get("sectors_delta")
    if not delta: return (0,0,0)
    sp=os.path.join(outdir,"sectors.json")
    if not os.path.exists(sp): return (0,0,0)
    doc=json.load(open(sp,encoding="utf-8"))
    sectors=doc.setdefault("sectors",[])
    bykey={s["key"]:s for s in sectors}
    ns=nn=ne=0
    # 1) 新規セクター
    for ns_def in delta.get("new_sectors",[]):
        k=ns_def.get("key")
        if not k or k in bykey: continue
        ns_def.setdefault("flow",{}).setdefault("nodes",{})
        ns_def["flow"].setdefault("edges",[])
        ns_def.setdefault("meta",{})
        sectors.append(ns_def); bykey[k]=ns_def; ns+=1
    # 2) 既存セクターへのノード追加
    for k,nodes in delta.get("add_nodes",{}).items():
        s=bykey.get(k)
        if not s: continue
        tgt=s.setdefault("flow",{}).setdefault("nodes",{})
        for nid,v in nodes.items():
            if nid not in tgt:
                tgt[nid]=v; nn+=1
    # 3) 既存セクターへのエッジ追加（重複はfrom/to/kindで判定）
    for k,edges in delta.get("add_edges",{}).items():
        s=bykey.get(k)
        if not s: continue
        tgt=s.setdefault("flow",{}).setdefault("edges",[])
        have={(e[0],e[1],e[2] if len(e)>2 else "") for e in tgt}
        for e in edges:
            sig=(e[0],e[1],e[2] if len(e)>2 else "")
            if sig not in have:
                tgt.append(e); have.add(sig); ne+=1
    # 3.5) 業界サマリ(総評)の上書き: summaries={"<key>":"総評1-2文"}
    for k,txt in delta.get("summaries",{}).items():
        s=bykey.get(k)
        if s and txt:
            s["summary"]=txt; s["summary_date"]=data.get("date_iso","")
    # 4) meta（企業・別名）の拡張
    for k,metas in delta.get("add_meta",{}).items():
        s=bykey.get(k)
        if not s: continue
        tmeta=s.setdefault("meta",{})
        for nid,m in metas.items():
            cur=tmeta.setdefault(nid,{"companies":[],"aliases":[]})
            cur.setdefault("companies",[]); cur.setdefault("aliases",[])
            have_co={ (c[0] if isinstance(c,list) else c) for c in cur["companies"] }
            for c in m.get("companies",[]):
                nm=c[0] if isinstance(c,list) else c
                if nm not in have_co:
                    cur["companies"].append(c); have_co.add(nm)
            for a in m.get("aliases",[]):
                if a not in cur["aliases"]:
                    cur["aliases"].append(a)
            # 解説(desc)・位置づけ理由(why) は上書き反映（新規ノードの解説を持たせる）
            for fld in ("desc","why"):
                if m.get(fld): cur[fld]=m[fld]
    json.dump(doc,open(sp,"w",encoding="utf-8"),ensure_ascii=False,indent=1)
    return (ns,nn,ne)

def _sector_summary(s):
    """業界ごとのポジ/ネガ サマリを作る。直近(ID末尾MMDD)のノードを2倍の重みで集計。"""
    nodes=s["flow"]["nodes"]; meta=s.get("meta",{})
    def recent(nid):
        m=re.search(r"(\d{4})$",nid); return m.group(1) if m else ""
    items=[]
    for nid,v in nodes.items():
        if v[2] not in ("pos","neg","mix"): continue
        m=meta.get(nid,{})
        items.append({"nid":nid,"sent":v[2],"title":v[3],"note":v[4] if len(v)>4 else "",
                      "why":m.get("why","") or (v[4] if len(v)>4 else ""),"rec":recent(nid)})
    w=lambda it: 2 if it["rec"] else 1
    P=sum(w(i) for i in items if i["sent"]=="pos"); N=sum(w(i) for i in items if i["sent"]=="neg")
    M=sum(w(i) for i in items if i["sent"]=="mix"); T=max(1,P+N+M)
    score=(P-N)/T
    if score>=0.35: stance=("追い風","#16a34a","#dcfce7")
    elif score>=0.1: stance=("やや追い風","#65a30d","#ecfccb")
    elif score>-0.1: stance=("強弱まちまち","#64748b","#f1f5f9")
    elif score>-0.35: stance=("やや逆風","#ea580c","#ffedd5")
    else: stance=("逆風","#dc2626","#fee2e2")
    order=lambda L: sorted(L,key=lambda i:(i["rec"]!="", i["rec"]),reverse=True)
    pos=order([i for i in items if i["sent"]=="pos"])[:4]
    neg=order([i for i in items if i["sent"]=="neg"])[:4]
    mix=order([i for i in items if i["sent"]=="mix"])[:3]
    latest=sorted([i for i in items if i["rec"]],key=lambda i:i["rec"],reverse=True)[:3]
    return {"stance":stance,"P":P,"N":N,"M":M,"T":T,"pos":pos,"neg":neg,"mix":mix,"latest":latest,
            "summary":s.get("summary",""),"summary_date":s.get("summary_date","")}

def _sumcard(sm):
    lab,fg,bg=sm["stance"]; T=sm["T"]
    bar=(f'<div class="sbar"><span style="width:{sm["P"]*100/T:.0f}%;background:#16a34a"></span>'
         f'<span style="width:{sm["M"]*100/T:.0f}%;background:#94a3b8"></span>'
         f'<span style="width:{sm["N"]*100/T:.0f}%;background:#dc2626"></span></div>')
    def li(it):
        d=f'<span class="sdt">{it["rec"][:2]}/{it["rec"][2:]}</span>' if it["rec"] else ''
        return f'<li><b>{esc(it["title"])}</b>{d}<div class="swhy">{esc(it["why"])}</div></li>'
    def col(cls,title,L,empty):
        return f'<div class="scol {cls}"><div class="sct">{title}</div><ul>{"".join(li(i) for i in L) or f"<li class=sempty>{empty}</li>"}</ul></div>'
    verdict=(f'<p class="sverdict"><span class="svl">総評</span>{esc(sm["summary"])}</p>') if sm["summary"] else ''
    return (f'<div class="ssum"><div class="shead"><span class="sbadge" style="color:{fg};background:{bg}">{lab}</span>'
            f'{bar}<span class="slegend">ポジ{sm["P"]}・中立{sm["M"]}・ネガ{sm["N"]}（直近の要素は2倍で集計）</span></div>{verdict}'
            f'<div class="scols">{col("spos","▲ 追い風（ポジ）",sm["pos"],"該当なし")}{col("sneg","▼ 逆風（ネガ）",sm["neg"],"目立った逆風なし")}'
            f'{col("smix","◆ 見極めポイント（中立）",sm["mix"],"—")}</div></div>')

SUM_CSS='''
 .ssum{border:1px solid #e2e8f0;border-radius:12px;padding:14px 16px;margin:4px 0 14px;background:#fbfcfe}
 .shead{display:flex;flex-wrap:wrap;align-items:center;gap:10px} .sbadge{font-weight:800;font-size:13px;padding:4px 12px;border-radius:20px;white-space:nowrap;flex-shrink:0}
 .sbar{display:flex;width:180px;height:9px;border-radius:5px;overflow:hidden;background:#e2e8f0} .sbar span{display:block;height:100%}
 .slegend{font-size:11.5px;color:#64748b}
 .sverdict{margin:10px 0 2px;font-size:13.5px;color:#0f172a;line-height:1.7} .svl{display:inline-block;font-size:11px;font-weight:800;color:#fff;background:#0f172a;border-radius:5px;padding:1px 7px;margin-right:8px}
 .scols{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px;margin-top:10px}
 .scol{border-radius:10px;padding:10px 12px} .scol ul{margin:6px 0 0;padding-left:16px} .scol li{font-size:12.5px;margin-bottom:6px}
 .spos{background:#f0fdf4;border:1px solid #bbf7d0} .sneg{background:#fef2f2;border:1px solid #fecaca} .smix{background:#f8fafc;border:1px solid #e2e8f0}
 .sct{font-size:12.5px;font-weight:800} .spos .sct{color:#15803d} .sneg .sct{color:#b91c1c} .smix .sct{color:#475569}
 .swhy{color:#475569;font-size:12px} .sdt{font-size:10.5px;color:#fff;background:#94a3b8;border-radius:4px;padding:0 5px;margin-left:6px}
 .sempty{color:#94a3b8;list-style:none;margin-left:-16px}
 .ovgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px}
 .ovc{display:block;text-decoration:none;color:#0f172a;border:1px solid #e2e8f0;border-radius:11px;padding:11px 13px;background:#fff}
 .ovc:hover{border-color:#94a3b8} .ovn{font-weight:800;font-size:13.5px;display:flex;justify-content:space-between;align-items:center;gap:6px}
 .ovc .sbar{width:100%;margin:7px 0 6px} .ovs{font-size:11.5px;color:#475569;line-height:1.55}
 .ovs b{font-weight:700} .ovp{color:#15803d} .ovneg{color:#b91c1c}
'''

def render_sectors(outdir):
    """分野別ビジネス構造マップ（バリューチェーン＋企業＋関連ニュース）。sectors.jsonが無ければスキップ。"""
    sp=os.path.join(outdir,"sectors.json")
    if not os.path.exists(sp): return 0
    secdef=json.load(open(sp,encoding="utf-8"))
    sectors=secdef.get("sectors",[])
    npath=os.path.join(outdir,"news.json")
    news=json.load(open(npath,encoding="utf-8")) if os.path.exists(npath) else []
    all_pops=[]; blocks=[]; toc=[]; sums=[]; _ssl=_sector_story_links(outdir)
    for s in sectors:
        key=s["key"]; name=s["name"]; col=s.get("color","#475569")
        flow=s["flow"]; nodes=flow["nodes"]; meta=s.get("meta",{})
        # node_meta: 各要素ノードにひも付く関連企業。node_news: 要素キーワード＋関連企業名でニュース抽出
        node_meta={}; node_news={}; allcos=[]
        for nid,v in nodes.items():
            title=v[3]; m=meta.get(nid,{})
            comps=m.get("companies",[])
            node_meta[nid]={"companies":comps}
            conames=[c[0] if isinstance(c,list) else c for c in comps]
            allcos+=conames
            al=list(m.get("aliases",[]))+conames
            node_news[nid]=_news_for_company(title, al, news, k=6)
        svg,pops=build_svg(flow, None, idbase=len(all_pops), node_news=node_news, node_meta=node_meta)
        all_pops.extend(pops)
        # 登場企業（重複排除・順序保持）
        seen=set(); uniq=[c for c in allcos if not (c in seen or seen.add(c))]
        clist="".join(f'<span class="chip">{esc(c)}</span>' for c in uniq)
        sm=_sector_summary(s); sums.append((s,sm))
        _rel=_ssl.get(key,[])
        _relh=(f'<div class="secchips" style="margin:-4px 0 12px"><span class="secl">関連する問い:</span>'+"".join(f'<a class="chip" style="text-decoration:none" href="./deepdives.html#st-{esc(x["id"])}">{esc(x["q"])}（{c}）</a>' for x,c in _rel)+'</div>') if _rel else ''

        toc.append(f'<a href="#sec-{key}">{esc(name)}</a>')
        blocks.append(f'''<section id="sec-{key}"><h2><span class="num" style="background:{col}">◆</span>{esc(name)}</h2>
   <p class="lead">{esc(s.get("lead",""))} 図のノードは<b>バリューチェーンの機能・工程（要素）</b>です。<b>各要素をタップ</b>すると、その工程に位置する<b>関連企業</b>と<b>関連ニュース</b>を表示します。</p>
   {_sumcard(sm)}{_relh}
   <div class="diagram">{svg}</div>{LEGEND}
   {f'<div class="secchips"><span class="secl">登場企業（{len(uniq)}社）:</span>{clist}</div>' if clist else ''}</section>''')
    def _ovc(s,sm):
        lab,fg,bg=sm["stance"]; T=sm["T"]
        p=sm["pos"][0]["title"] if sm["pos"] else "—"; n=sm["neg"][0]["title"] if sm["neg"] else "目立った逆風なし"
        return (f'<a class="ovc" href="#sec-{s["key"]}"><div class="ovn">{esc(s["name"])}<span class="sbadge" style="color:{fg};background:{bg};font-size:11px;padding:2px 8px">{lab}</span></div>'
                f'<div class="sbar"><span style="width:{sm["P"]*100/T:.0f}%;background:#16a34a"></span><span style="width:{sm["M"]*100/T:.0f}%;background:#94a3b8"></span><span style="width:{sm["N"]*100/T:.0f}%;background:#dc2626"></span></div>'
                f'<div class="ovs"><span class="ovp">▲</span> {esc(p)}<br><span class="ovneg">▼</span> {esc(n)}</div></a>')
    overview=(f'<section id="overview"><h2><span class="num">◎</span>業界別サマリ（ポジ／ネガ）</h2><p class="lead">各業界の要素を「追い風（ポジ）」「逆風（ネガ）」「中立」に分けて集計し、直近のニュースで加わった要素を重く数えて判定しています。カードをタップすると各業界の詳細へ移動します。</p>'
              f'<div class="ovgrid">{"".join(_ovc(s,sm) for s,sm in sums)}</div></section>')
    body=f'''<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>業界構造マップ｜ビジネスニュース・ダッシュボード</title><style>{CSS}{CSS_EXTRA}{MODAL_CSS}{SECTOR_CSS}{SUM_CSS}</style></head><body><div class="wrap">
 <header><div class="eyebrow">BUSINESS NEWS — SECTOR MAP</div><h1>業界構造マップ（バリューチェーン）</h1>
   <div class="sub">分野ごとの「ビジネスの流れ」と主要プレイヤーの結びつき。上流→中流→下流→市場の順に、企業がどこで価値を生むかを俯瞰。全{len(sectors)}分野</div>
   <div class="home"><a href="./index.html">← ダッシュボードへ戻る</a></div>
   <nav class="toc"><a href="#overview"><b>業界別サマリ</b></a>{"".join(toc)}</nav></header>
 {overview}
 {"".join(blocks)}
 <footer>Cowork ビジネスニュース・ダッシュボード ／ 業界構造マップ</footer></div>{BN_MODAL}{bn_script(all_pops)}</body></html>'''
    open(os.path.join(outdir,"sectors.html"),"w",encoding="utf-8").write(body)
    return len(sectors)

MONTH_CSS='''
 .mtop{display:flex;gap:12px;align-items:baseline;padding:8px 0;border-bottom:1px solid #eef2f7}
 .mtd{font-size:11.5px;color:#94a3b8;font-weight:700;min-width:82px} .mth{font-size:13.5px;color:#0f172a;text-decoration:none;font-weight:600}
 .mth:hover{color:#2563eb} .mbars{display:flex;flex-direction:column;gap:7px}
 .mbar{display:flex;align-items:center;gap:10px} .mbl{font-size:12px;color:#475569;min-width:120px;text-align:right}
 .mbt{flex:1;background:#f1f5f9;border-radius:6px;height:14px;overflow:hidden} .mbf{display:block;height:100%;border-radius:6px}
 .mbn{font-size:12px;color:#64748b;min-width:26px;font-weight:700}
'''
SECTOR_CSS='''
 .secchips{margin-top:12px;display:flex;flex-wrap:wrap;gap:6px;align-items:center} .secl{font-size:12px;font-weight:700;color:#475569;margin-right:4px}
'''

def update_stores(d,outdir):
    # masterflow.json: 全体連動マップ（毎回上書き更新）
    if d.get("masterflow") and d["masterflow"].get("nodes"):
        json.dump(d["masterflow"],open(os.path.join(outdir,"masterflow.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=1)
    # trends.json: overwrite with latest snapshot
    if d.get("trends"):
        json.dump(d["trends"],open(os.path.join(outdir,"trends.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=1)
    # news.json: 日次ニュースを累積（headで重複排除・新しい順・最大900件）。連動マップのノード→ニュース紐付けに使用
    np=os.path.join(outdir,"news.json")
    nlib=json.load(open(np,encoding="utf-8")) if os.path.exists(np) else []
    nseen={n.get("head") for n in nlib}
    for n in d.get("news",[]):
        if n.get("head") in nseen: continue
        nseen.add(n.get("head"))
        nlib.insert(0,{"ind":n.get("ind",""),"head":n.get("head",""),"summ":n.get("summ",""),
                       "url":n.get("url",""),"date":d.get("date_iso","")})
    nlib=nlib[:900]
    json.dump(nlib,open(np,"w",encoding="utf-8"),ensure_ascii=False,indent=1)
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
    iso=d.get("date_iso","")
    # companies.json: accumulate (dedupe by code/name), preserve financial fields
    cp=os.path.join(outdir,"companies.json")
    comps=json.load(open(cp,encoding="utf-8")) if os.path.exists(cp) else []
    cidx={ (r.get("code") or r.get("name")): r for r in comps }
    cadd=0
    for c in d.get("companies",[]):
        name=canon(c[0]); code=(c[1] if len(c)>1 else "").strip()
        key=code if code and code!="—" else name
        summ=c[4] if len(c)>4 else ""
        r=cidx.get(key)
        if r:
            r["name"]=name
            if c[2] if len(c)>2 else "": r["ind"]=c[2]
            if len(c)>3 and c[3] and c[3]!="—": r["cap"]=c[3]
            if summ: r["summ"]=summ
            if iso and iso>=r.get("last",""): r["last"]=iso
            if iso and iso<r.get("first","9999"): r["first"]=iso
        else:
            r={"name":name,"code":code,"ind":c[2] if len(c)>2 else "","cap":c[3] if len(c)>3 else "—",
               "summ":summ,"first":iso,"last":iso,"revenue":"—","per":"—","pbr":"—","roe":"—","outlook":""}
            comps.append(r); cidx[key]=r; cadd+=1
    json.dump(comps,open(cp,"w",encoding="utf-8"),ensure_ascii=False,indent=1)
    # predictions.json: accumulate (dedupe by leading text), newest first
    pp=os.path.join(outdir,"predictions.json")
    preds=json.load(open(pp,encoding="utf-8")) if os.path.exists(pp) else []
    pseen={p["what"][:26] for p in preds}
    padd=0
    for p in d.get("preds",[]):
        what=p[0]; k=what[:26]
        if k in pseen: continue
        pseen.add(k)
        hz=p[3] if len(p)>3 and p[3] else pred_horizon(what)
        preds.insert(0,{"what":what,"conf":p[1] if len(p)>1 else "中","comp":p[2] if len(p)>2 else "","horizon":hz,"date":iso})
        padd+=1
    json.dump(preds,open(pp,"w",encoding="utf-8"),ensure_ascii=False,indent=1)
    return added,cadd,padd


# ===================== 掘り下げストーリー（問いで束ねる） =====================
def _load_stories(outdir):
    sp=os.path.join(outdir,"stories.json")
    if not os.path.exists(sp): return None
    return json.load(open(sp,encoding="utf-8"))

def _pick_story(doc, e):
    t=e[0]
    for sub,sid in doc.get("overrides",{}).items():
        if sub in t: return sid
    for st in doc["stories"]:
        if any(w in t for w in st.get("kws",[])): return st["id"]
    for st in doc["stories"]:
        if any(w in str(e[1])[:120] for w in st.get("kws",[])): return st["id"]
    return "misc"

def merge_stories(d, outdir):
    """day_data の stories_delta / story_map を stories.json に反映し、当日の掘り下げを問いに振り分ける。
    stories_delta={"new":[{id,q,sector,kws,lead}], "leads":{id:"見立て"}}, story_map={"掘り下げトピック":"story_id"}"""
    doc=_load_stories(outdir)
    if doc is None: return (0,0)
    iso=d.get("date_iso","")
    byid={s["id"]:s for s in doc["stories"]}
    delta=d.get("stories_delta") or {}
    nnew=0
    for s in delta.get("new",[]):
        if not s.get("id") or s["id"] in byid: continue
        s.setdefault("kws",[]); s.setdefault("sector",""); s["lead_date"]=iso; s["created"]=iso
        doc["stories"].insert(len(doc["stories"])-1 if doc["stories"] and doc["stories"][-1]["id"]=="misc" else len(doc["stories"]), s)
        byid[s["id"]]=s; nnew+=1
    for sid,txt in delta.get("leads",{}).items():
        if sid in byid and txt:
            byid[sid]["lead"]=txt; byid[sid]["lead_date"]=iso
    assign=doc.setdefault("assign",{})
    smap=d.get("story_map") or {}
    nas=0
    for e in d.get("deeps",[]):
        t=e[0]
        sid=smap.get(t)
        if sid not in byid: sid=assign.get(t) or _pick_story(doc,e)
        if assign.get(t)!=sid: assign[t]=sid; nas+=1
    json.dump(doc,open(os.path.join(outdir,"stories.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=1)
    return (nnew,nas)

def _story_groups(outdir):
    """stories と deepdives を結合。戻り値: [(story, [entries newest first])] 最新更新順"""
    doc=_load_stories(outdir)
    dp=os.path.join(outdir,"deepdives.json")
    deeps=json.load(open(dp,encoding="utf-8")) if os.path.exists(dp) else []
    if doc is None: return [],deeps
    byid={s["id"]:s for s in doc["stories"]}; mem={s["id"]:[] for s in doc["stories"]}
    for e in deeps:
        sid=doc.get("assign",{}).get(e[0]) or _pick_story(doc,e)
        if sid not in mem: sid="misc"
        mem.setdefault(sid,[]).append(e)
    out=[]
    for s in doc["stories"]:
        L=sorted(mem.get(s["id"],[]),key=lambda e:(e[4] if len(e)>4 else ""),reverse=True)
        if L: out.append((s,L))
    out.sort(key=lambda x:(x[0]["id"]!="misc", x[1][0][4] if len(x[1][0])>4 else "", len(x[1])),reverse=True)
    return out,deeps

def _latest_digest_date(outdir):
    fs=sorted(glob.glob(os.path.join(outdir,"digest_*.html")),reverse=True)
    m=re.search(r"(\d{4}-\d{2}-\d{2})",os.path.basename(fs[0])) if fs else None
    return m.group(1) if m else ""

def _days_between(a,b):
    import datetime as _d
    try: return (_d.date.fromisoformat(a)-_d.date.fromisoformat(b)).days
    except Exception: return 999

SECTOR_NAME_CACHE={}
def _sector_names(outdir):
    sp=os.path.join(outdir,"sectors.json")
    if not os.path.exists(sp): return {}
    return {s["key"]:s["name"] for s in json.load(open(sp,encoding="utf-8")).get("sectors",[])}

STORY_CSS='''
 .stsearch{width:100%;padding:11px 14px;border:1px solid #cbd5e1;border-radius:10px;font-size:14px;margin:4px 0 12px;background:#fff}
 .stfil{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px} .stfil button{border:1px solid #e2e8f0;background:#fff;border-radius:20px;padding:4px 11px;font-size:12px;cursor:pointer;color:#334155}
 .stfil button.on{background:#0f172a;color:#fff;border-color:#0f172a}
 details.story{border:1px solid #e2e8f0;border-radius:13px;margin-bottom:12px;background:#fff;overflow:hidden;scroll-margin-top:12px}
 details.story>summary{list-style:none;cursor:pointer;padding:14px 16px} details.story>summary::-webkit-details-marker{display:none}
 details.story[open]{box-shadow:0 3px 14px rgba(15,23,42,.07)}
 .stq{font-size:15.5px;font-weight:800;color:#0f172a;display:flex;gap:8px;align-items:baseline;flex-wrap:wrap}
 .stq::before{content:"Q";display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:6px;background:#0f172a;color:#fff;font-size:12px;flex-shrink:0}
 .stmeta{font-size:11.5px;color:#64748b;margin-top:5px;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
 .stnew{background:#dc2626;color:#fff;border-radius:5px;padding:0 6px;font-weight:800;font-size:10.5px}
 .stsec{background:#f1f5f9;border-radius:20px;padding:1px 9px;color:#334155;text-decoration:none}
 .stlead{font-size:13px;color:#334155;margin-top:8px;line-height:1.7;background:#f8fafc;border-left:3px solid #0f172a;border-radius:6px;padding:8px 11px}
 .stlead b{font-size:11px;color:#0f172a;margin-right:6px}
 .stbody{padding:4px 16px 14px;border-top:1px dashed #eef2f7}
 .sttl{position:relative;margin:8px 0 0 6px;padding-left:16px;border-left:2px solid #e2e8f0}
 details.stitem{margin:0 0 8px;position:relative} details.stitem>summary{list-style:none;cursor:pointer;font-size:13px;color:#0f172a;font-weight:600;padding:4px 0}
 details.stitem>summary::-webkit-details-marker{display:none}
 details.stitem>summary::before{content:"";position:absolute;left:-22px;top:10px;width:10px;height:10px;border-radius:50%;background:#94a3b8;border:2px solid #fff}
 details.stitem:first-child>summary::before{background:#0f172a}
 .stdt{font-size:11px;color:#94a3b8;font-weight:700;margin-right:8px}
 .stdet{font-size:12.5px;color:#334155;padding:4px 0 8px} .stdet .dcomp{font-size:11.5px;color:#64748b}
 .stgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:10px}
 a.stcard{display:block;border:1px solid #e2e8f0;border-radius:12px;padding:12px 14px;text-decoration:none;color:#0f172a;background:#fff}
 a.stcard:hover{border-color:#94a3b8;box-shadow:0 3px 10px rgba(15,23,42,.06)}
 .stcq{font-weight:800;font-size:13.5px;line-height:1.5} .stcl{font-size:12px;color:#475569;margin-top:6px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
 .stcm{font-size:11px;color:#94a3b8;margin-top:7px;display:flex;gap:8px;align-items:center}
 .sthide{display:none!important}
'''

def render_deepdives(outdir):
    groups,deeps=_story_groups(outdir)
    if not groups: return 0
    latest=_latest_digest_date(outdir); sn=_sector_names(outdir)
    blocks=[]; secs=[]
    for s,L in groups:
        last=L[0][4] if len(L[0])>4 else ""
        new=(_days_between(latest,last)<=1) if last else False
        items=[]
        for e in L:
            dt=e[4] if len(e)>4 else ""
            items.append(f'<details class="stitem" data-t="{esc((e[0]+" "+str(e[1])+" "+str(e[2])).lower())}"><summary><span class="stdt">{esc(dt)}</span>{esc(e[0])}</summary><div class="stdet"><p>{esc(e[1])}</p><div class="dcomp">関連: {esc(e[2])}</div><h4 style="font-size:12px;color:#0891b2;margin:8px 0 4px">キーワード・構造解説</h4><ul class="terms">{deep_terms_html(e[3])}</ul></div></details>')
        secname=sn.get(s.get("sector",""),"")
        if secname and secname not in secs: secs.append(secname)
        seclink=f'<a class="stsec" href="./sectors.html#sec-{esc(s["sector"])}" onclick="event.stopPropagation()">{esc(secname)}</a>' if secname else ''
        ld=f'（{esc(s["lead_date"])}更新）' if s.get("lead_date") else ''
        blocks.append(f'''<details class="story" id="st-{esc(s["id"])}" data-sec="{esc(secname)}" data-q="{esc((s["q"]+" "+s.get("lead","")).lower())}"><summary>
  <div class="stq">{esc(s["q"])}{'<span class="stnew">NEW</span>' if new else ''}</div>
  <div class="stmeta">{seclink}<span>掘り下げ {len(L)}件</span><span>最終更新 {esc(last)}</span><span>{esc(s.get("created",""))}〜</span></div>
  <div class="stlead"><b>いまの見立て{ld}</b>{esc(s.get("lead",""))}</div></summary>
  <div class="stbody"><div class="sttl">{"".join(items)}</div></div></details>''')
    fil='<button class="on" data-f="">すべて</button>'+"".join(f'<button data-f="{esc(x)}">{esc(x)}</button>' for x in secs)
    js='''<script>(function(){var q=document.getElementById("stq"),f="",bs=document.querySelectorAll(".stfil button");
function run(){var v=(q.value||"").trim().toLowerCase();document.querySelectorAll("details.story").forEach(function(s){
 var okf=!f||s.dataset.sec===f,its=s.querySelectorAll("details.stitem"),hit=0;
 its.forEach(function(i){var m=!v||i.dataset.t.indexOf(v)>=0||s.dataset.q.indexOf(v)>=0;i.classList.toggle("sthide",!m);if(m)hit++;});
 var show=okf&&(hit>0);s.classList.toggle("sthide",!show);if(v&&show)s.open=true;});}
q.addEventListener("input",run);bs.forEach(function(b){b.onclick=function(){bs.forEach(function(x){x.classList.remove("on")});b.classList.add("on");f=b.dataset.f;run();};});
if(location.hash){var t=document.querySelector(location.hash);if(t&&t.tagName==="DETAILS"){t.open=true;}}})();</script>'''
    body=f'''<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>掘り下げ：問いで追う論点｜ビジネスニュース・ダッシュボード</title><style>{CSS}{STORY_CSS}</style></head><body><div class="wrap">
 <header><div class="eyebrow">BUSINESS NEWS — DEEP DIVES</div><h1>掘り下げ：問いで追う論点</h1>
   <div class="sub">日々の掘り下げ{len(deeps)}件を、{len(groups)}本の「問い」に束ねました。各問いに「いまの見立て」と、論点の推移（新しい順）を載せています。</div>
   <div class="home"><a href="./index.html">← ダッシュボードへ戻る</a></div></header>
 <section><input id="stq" class="stsearch" type="search" placeholder="キーワードで検索（例：HBM、地銀、介入、ナフサ）">
 <div class="stfil">{fil}</div>
 {"".join(blocks)}</section>
 <footer>Cowork ビジネスニュース・ダッシュボード ／ 掘り下げライブラリ</footer></div>{js}</body></html>'''
    open(os.path.join(outdir,"deepdives.html"),"w",encoding="utf-8").write(body)
    return len(groups)

def _story_cards_html(outdir, k=None):
    groups,deeps=_story_groups(outdir)
    latest=_latest_digest_date(outdir)
    cards=[]
    for s,L in (groups if k is None else groups[:k]):
        last=L[0][4] if len(L[0])>4 else ""
        new=(_days_between(latest,last)<=1) if last else False
        cards.append(f'<a class="stcard" href="./deepdives.html#st-{esc(s["id"])}"><div class="stcq">{esc(s["q"])}</div><div class="stcl">{esc(s.get("lead",""))}</div><div class="stcm">{"<span class=stnew>NEW</span>" if new else ""}<span>{len(L)}件</span><span>最終 {esc(last[5:] if last else "")}</span></div></a>')
    return "".join(cards), len(groups), len(deeps)

def _sector_story_links(outdir):
    groups,_=_story_groups(outdir); m={}
    for s,L in groups:
        if s.get("sector"): m.setdefault(s["sector"],[]).append((s,len(L)))
    return m

# ===================== 更新ログ（デイリーで何が変わったか） =====================
def track_masterflow(d, outdir):
    """masterflow.json を上書きする前に呼ぶ。前日版との差分を changelog.json に記録（同日再実行でも基準は前日版）"""
    nf=d.get("masterflow") or {}
    if not nf.get("nodes"): return 0
    iso=d.get("date_iso",""); cp=os.path.join(outdir,"changelog.json")
    log=json.load(open(cp,encoding="utf-8")) if os.path.exists(cp) else {"mf":{},"mf_last":{}}
    last=log.get("mf_last",{})
    if last.get("date")==iso: prev=last.get("prev_nodes",{})
    else:
        mp=os.path.join(outdir,"masterflow.json")
        prev=json.load(open(mp,encoding="utf-8")).get("nodes",{}) if os.path.exists(mp) else {}
    cur=nf["nodes"]; ch=[]
    for k,v in cur.items():
        o=prev.get(k)
        if o is None: ch.append(["new",v[3],v[2]])
        elif o[2]!=v[2]: ch.append(["sent",v[3],o[2]+"→"+v[2]])
        elif o[3]!=v[3]: ch.append(["title",v[3],o[3]])
    for k,o in prev.items():
        if k not in cur: ch.append(["del",o[3],o[2]])
    ntext=sum(1 for k,v in cur.items() if k in prev and prev[k][2]==v[2] and prev[k][3]==v[3] and (prev[k][4] if len(prev[k])>4 else "")!=(v[4] if len(v)>4 else ""))
    log.setdefault("mf",{})[iso]={"changes":ch,"notes":ntext}
    log["mf_last"]={"date":iso,"prev_nodes":prev}
    json.dump(log,open(cp,"w",encoding="utf-8"),ensure_ascii=False,indent=1)
    return len(ch)

def _stance_asof(s, mmdd):
    nodes={k:v for k,v in s["flow"]["nodes"].items() if not re.search(r"(\d{4})$",k) or re.search(r"(\d{4})$",k).group(1)<=mmdd}
    s2=dict(s); s2["flow"]={"nodes":nodes,"edges":[]}
    return _sector_summary(s2)["stance"][0]

def build_updates(outdir, ndays=60):
    files=sorted(glob.glob(os.path.join(outdir,"digest_*.html")),reverse=True)
    dates=[re.search(r"(\d{4}-\d{2}-\d{2})",os.path.basename(f)).group(1) for f in files][:ndays+1]
    sp=os.path.join(outdir,"sectors.json"); sectors=json.load(open(sp,encoding="utf-8")).get("sectors",[]) if os.path.exists(sp) else []
    news=json.load(open(os.path.join(outdir,"news.json"),encoding="utf-8")) if os.path.exists(os.path.join(outdir,"news.json")) else []
    preds=json.load(open(os.path.join(outdir,"predictions.json"),encoding="utf-8")) if os.path.exists(os.path.join(outdir,"predictions.json")) else []
    comps=json.load(open(os.path.join(outdir,"companies.json"),encoding="utf-8")) if os.path.exists(os.path.join(outdir,"companies.json")) else []
    cp=os.path.join(outdir,"changelog.json"); log=json.load(open(cp,encoding="utf-8")) if os.path.exists(cp) else {}
    doc=_load_stories(outdir) or {"stories":[],"assign":{}}; sq={s["id"]:s["q"] for s in doc["stories"]}
    dp=os.path.join(outdir,"deepdives.json"); deeps=json.load(open(dp,encoding="utf-8")) if os.path.exists(dp) else []
    byday={}
    for n in news:
        if n.get("date"): byday.setdefault(n["date"],[]).append(n)
    out=[]
    for i,dt in enumerate(dates[:ndays]):
        prevd=dates[i+1] if i+1<len(dates) else None
        mm=dt[5:7]+dt[8:10]; pmm=(prevd[5:7]+prevd[8:10]) if prevd else None
        tops=list(reversed(byday.get(dt,[])))[:3]
        stance=[]; nodes=[]; sums=[]
        for s in sectors:
            if pmm:
                a=_stance_asof(s,pmm); b=_stance_asof(s,mm)
                if a!=b: stance.append((s["key"],s["name"],a,b))
            add=[v[3] for k,v in s["flow"]["nodes"].items() if re.search(r"(\d{4})$",k) and re.search(r"(\d{4})$",k).group(1)==mm]
            if add: nodes.append((s["key"],s["name"],add))
            if s.get("summary_date")==dt: sums.append((s["key"],s["name"]))
        dps=[(e[0],sq.get(doc["assign"].get(e[0],""),"")) for e in deeps if len(e)>4 and e[4]==dt]
        pr=[p for p in preds if p.get("date")==dt]
        cs=[c.get("name","") for c in comps if c.get("first")==dt]
        leads=[(s["id"],s["q"]) for s in doc["stories"] if s.get("lead_date")==dt]
        mf=log.get("mf",{}).get(dt)
        out.append({"date":dt,"tops":tops,"stance":stance,"nodes":nodes,"sums":sums,"deeps":dps,"preds":pr,"comps":cs,"leads":leads,"mf":mf,"nnews":len(byday.get(dt,[]))})
    return out

UPD_CSS='''
 .uday{border:1px solid #e2e8f0;border-radius:13px;background:#fff;padding:14px 16px;margin-bottom:12px}
 .udh{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap} .udd{font-size:16px;font-weight:800} .udn{font-size:11.5px;color:#64748b}
 .udh a{margin-left:auto;font-size:12px;color:#2563eb;text-decoration:none}
 .urow{display:flex;gap:10px;margin-top:9px;font-size:12.8px;line-height:1.6} .ulab{flex-shrink:0;width:96px;font-size:11px;font-weight:800;color:#475569;padding-top:2px}
 .uval{flex:1;color:#1e293b} .uval a{color:#1e293b} .uval ol{margin:0;padding-left:18px}
 .uchip{display:inline-block;background:#f1f5f9;border-radius:7px;padding:1px 8px;margin:0 4px 4px 0;font-size:12px}
 .uup{background:#dcfce7;color:#15803d} .udown{background:#fee2e2;color:#b91c1c}
 .today{border:2px solid #0f172a;border-radius:16px;background:#fff;padding:16px 18px;margin-top:18px}
 .today h2{margin-bottom:6px}
 @media (max-width:640px){.urow{flex-direction:column;gap:2px}.ulab{width:auto}}
'''
_RANK={"逆風":0,"やや逆風":1,"強弱まちまち":2,"やや追い風":3,"追い風":4}
def _upd_rows(u, compact=False):
    rows=[]
    if u["tops"]:
        rows.append(("トップ記事","<ol>"+"".join(f'<li><a href="{esc(t.get("url","#"))}" target="_blank" rel="noopener">{esc(t.get("head",""))}</a></li>' for t in u["tops"])+"</ol>"))
    if u["stance"]:
        rows.append(("業界の潮目","".join(f'<a class="uchip {"uup" if _RANK.get(b,2)>_RANK.get(a,2) else "udown"}" href="./sectors.html#sec-{esc(k)}">{esc(n)}：{esc(a)} → <b>{esc(b)}</b></a>' for k,n,a,b in u["stance"])))
    if u["nodes"]:
        if compact: rows.append(("構造マップ","".join(f'<a class="uchip" href="./sectors.html#sec-{esc(k)}">{esc(n)} +{len(a)}</a>' for k,n,a in u["nodes"])))
        else: rows.append(("構造マップに追加","".join(f'<div><a href="./sectors.html#sec-{esc(k)}"><b>{esc(n)}</b></a>：{esc("、".join(a))}</div>' for k,n,a in u["nodes"])))
    if u["sums"]:
        rows.append(("総評を更新","".join(f'<a class="uchip" href="./sectors.html#sec-{esc(k)}">{esc(n)}</a>' for k,n in u["sums"])))
    if u["mf"] and u["mf"].get("changes"):
        lab={"new":"追加","sent":"符号変化","title":"見出し変更","del":"削除"}
        ch=u["mf"]["changes"]
        rows.append(("全体連動マップ","".join(f'<span class="uchip">{lab[c[0]]}：{esc(c[1])}{("（"+esc(c[2])+"）") if c[0]=="sent" else ""}</span>' for c in ch[:8])+(f'<span class="uchip">他{len(ch)-8}件</span>' if len(ch)>8 else "")))
    if u["deeps"]:
        rows.append(("掘り下げ","".join(f'<div>🔎 {esc(t)}{("<span style=color:#64748b>（"+esc(q)+"）</span>") if q and not compact else ""}</div>' for t,q in u["deeps"])))
    if u["leads"]:
        rows.append(("見立てを更新","".join(f'<a class="uchip" href="./deepdives.html#st-{esc(i)}">{esc(q)}</a>' for i,q in u["leads"])))
    if u["preds"] and not compact:
        rows.append(("新しい予測","<ol>"+"".join(f'<li>{esc(p.get("what",""))}<span style="color:#94a3b8">（確度{esc(p.get("conf",""))}・{esc(p.get("horizon",""))}）</span></li>' for p in u["preds"])+"</ol>"))
    elif u["preds"]:
        rows.append(("新しい予測",f'{len(u["preds"])}件'))
    if u["comps"]:
        rows.append(("新登場の企業","、".join(esc(c) for c in u["comps"][:12])+(f" 他{len(u['comps'])-12}社" if len(u["comps"])>12 else "")))
    return "".join(f'<div class="urow"><div class="ulab">{a}</div><div class="uval">{b}</div></div>' for a,b in rows)

def _wdj(iso):
    import datetime as _d
    try: return "月火水木金土日"[_d.date.fromisoformat(iso).weekday()]
    except Exception: return ""

def render_updates(outdir):
    ups=build_updates(outdir, ndays=60)
    if not ups: return 0
    cards="".join(f'<div class="uday" id="u-{u["date"]}"><div class="udh"><span class="udd">{int(u["date"][5:7])}/{int(u["date"][8:])}（{_wdj(u["date"])}）</span><span class="udn">ニュース{u["nnews"]}本</span><a href="./digest_{u["date"]}.html">日次を開く →</a></div>{_upd_rows(u)}</div>' for u in ups)
    body=f'''<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>更新ログ｜ビジネスニュース・ダッシュボード</title><style>{CSS}{UPD_CSS}</style></head><body><div class="wrap">
 <header><div class="eyebrow">BUSINESS NEWS — CHANGELOG</div><h1>更新ログ（毎日の変化）</h1>
   <div class="sub">日々のダイジェストで何が追加・変化したかを1日1枚にまとめています（直近60日分・新しい順）。「業界の潮目」は業界サマリの判定ラベルが変わった業界です。全体連動マップの変化は2026年10月21日分から記録しています。</div>
   <div class="home"><a href="./index.html">← ダッシュボードへ戻る</a></div></header>
 {cards}
 <footer>Cowork ビジネスニュース・ダッシュボード ／ 更新ログ</footer></div></body></html>'''
    open(os.path.join(outdir,"updates.html"),"w",encoding="utf-8").write(body)
    return len(ups)

def _today_box(outdir):
    ups=build_updates(outdir, ndays=1)
    if not ups: return ""
    u=ups[0]
    return f'''<section class="today" id="today"><h2><span class="num">★</span>今日の変化（{int(u["date"][5:7])}/{int(u["date"][8:])}・{_wdj(u["date"])}）</h2>
 <p class="lead" style="margin-bottom:4px">前回のダイジェストから何が変わったか。過去分は<a href="./updates.html">更新ログ</a>で日付順に追えます。</p>{_upd_rows(u, compact=True)}</section>'''

# ===================== いまの全体像（マップ＋業界カード） =====================
TREND2SEC=[("AI","semi aiinfra aiinfra_power humanoid agentai"),("半導体","semi aiinfra"),("金融","fin"),("エネルギー","energy refining trading"),
 ("財政","fiscal"),("政治","fiscal"),("防衛","defense shipping aviation"),("宇宙","defense"),("小売","retail"),("食品","retail"),
 ("自動車","auto"),("モビリティ","auto aviation"),("不動産","construction resilience"),("建設","construction resilience"),
 ("通信","telecom sovai"),("サイバー","sovai"),("海外","trading"),("製薬","pharma"),("ヘルスケア","pharma"),("人材","labor"),("労働","labor"),("エンタメ","media"),("商社","trading"),("海運","shipping")]
OV_CSS='''
 .ovwrap{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;margin-top:6px}
 .ovcard{border:1px solid #e2e8f0;border-radius:13px;background:#fff;padding:13px 15px}
 .ovt{font-weight:800;font-size:14.5px;margin-bottom:4px} .ovd{font-size:12.5px;color:#475569;line-height:1.65}
 .ovsub{margin-top:9px;border-top:1px dashed #e2e8f0;padding-top:8px;display:flex;flex-direction:column;gap:6px}
 a.ovs2{display:flex;align-items:center;gap:8px;text-decoration:none;color:#0f172a;font-size:12.5px}
 a.ovs2:hover .ovsn{text-decoration:underline} .ovsn{flex:1;font-weight:700} .ovs2 .sbar{width:70px;height:7px}
 .ovb{font-size:10.5px;font-weight:800;padding:1px 7px;border-radius:12px;white-space:nowrap}
 .ovpn{font-size:11.5px;color:#475569;margin-top:6px;line-height:1.55} .ovpn .p{color:#15803d;font-weight:800} .ovpn .n{color:#b91c1c;font-weight:800}
 .subh{font-size:14px;font-weight:800;margin:20px 0 4px;color:#0f172a}
'''
def _overview_cards(outdir, trends):
    sp=os.path.join(outdir,"sectors.json")
    sectors={s["key"]:s for s in json.load(open(sp,encoding="utf-8")).get("sectors",[])} if os.path.exists(sp) else {}
    sm={k:_sector_summary(s) for k,s in sectors.items()}
    used=set(); cards=[]
    def subrow(k):
        s=sectors[k]; x=sm[k]; lab,fg,bg=x["stance"]; T=x["T"]
        bar=(f'<span class="sbar"><span style="width:{x["P"]*100/T:.0f}%;background:#16a34a"></span><span style="width:{x["M"]*100/T:.0f}%;background:#94a3b8"></span><span style="width:{x["N"]*100/T:.0f}%;background:#dc2626"></span></span>')
        return f'<a class="ovs2" href="./sectors.html#sec-{k}"><span class="ovsn">{esc(s["name"])}</span>{bar}<span class="ovb" style="color:{fg};background:{bg}">{lab}</span></a>'
    def pn(keys):
        P=[i for k in keys for i in sm[k]["pos"]]; N=[i for k in keys for i in sm[k]["neg"]]
        key=lambda i:i["rec"]
        P=sorted(P,key=key,reverse=True); N=sorted(N,key=key,reverse=True)
        return (f'<div class="ovpn">{"<span class=p>▲</span> "+esc(P[0]["title"]) if P else ""}{"<br>" if P and N else ""}{"<span class=n>▼</span> "+esc(N[0]["title"]) if N else ""}</div>')
    for name,col,txt in trends:
        keys=[]
        for kw,ks in TREND2SEC:
            if kw in name:
                for k in ks.split():
                    if k in sectors and k not in keys and k not in used: keys.append(k)
        used.update(keys)
        sub=("<div class=ovsub>"+"".join(subrow(k) for k in keys)+"</div>"+pn(keys)) if keys else ""
        cards.append(f'<div class="ovcard" style="border-top:3px solid {col}"><div class="ovt" style="color:{col}">{esc(name)}</div><div class="ovd">{esc(txt)}</div>{sub}</div>')
    rest=[k for k in sectors if k not in used]
    if rest:
        cards.append(f'<div class="ovcard" style="border-top:3px solid #94a3b8"><div class="ovt" style="color:#475569">その他の業界</div><div class="ovd">上記の大分類に含まれない業界の判定です。</div><div class="ovsub">{"".join(subrow(k) for k in rest)}</div>{pn(rest)}</div>')
    return "".join(cards)


if __name__=="__main__":
    data=json.load(open(sys.argv[1],encoding="utf-8"))
    outdir=sys.argv[2] if len(sys.argv)>2 else "."
    iso=data["date_iso"]
    out=os.path.join(outdir,f"digest_{iso}.html")
    open(out,"w",encoding="utf-8").write(render_daily(data))
    nmf=track_masterflow(data,outdir)
    added,cadd,padd=update_stores(data,outdir)
    st_new,st_as=merge_stories(data,outdir)
    ncomp=render_companies(outdir)
    npred=render_predictions(outdir)
    ym=render_month(outdir, iso)
    sadd=merge_sectors_delta(data, outdir)
    nsec=render_sectors(outdir)
    nst=render_deepdives(outdir)
    nup=render_updates(outdir)
    n,nd,nt=render_index(outdir)
    smsg=f"{nsec}" + (f" (+{sadd[0]}sec/+{sadd[1]}node/+{sadd[2]}edge)" if any(sadd) else "")
    print(f"wrote {out} | index: {n} digests, deepdive {nd} (+{added}), trends {nt} | companies {ncomp} (+{cadd}), predictions {npred} (+{padd}) | month {ym} | sectors {smsg} | stories {nst} (+{st_new}new/{st_as}assigned) | masterflow changes {nmf} | updates {nup}days")
