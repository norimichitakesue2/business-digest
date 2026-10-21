
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
        new=(_days_between(latest,last)<=3) if last else False
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
        new=(_days_between(latest,last)<=3) if last else False
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
