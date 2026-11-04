# -*- coding: utf-8 -*-
"""世界の流れ（7本のマクロ潮流）と企業のつながりの蓄積・描画。
build_digest.py から呼ばれる:
  merge_world(day_data, outdir) -> streams.json / world_news.json / world_arrows.json / moves.json / world_cos.json を更新
  render_world(outdir)          -> world.html を生成
  index_teaser(outdir)          -> index.html 用の「世界の流れ」ブロック
  flags_html(codes)             -> 国旗<img>（flags/xx.svg）
day_data.json の追加フィールド（すべて任意）:
  news[i].world = {"s":"<流れid>","c":["jp","us"],"t":"pos|neg|mix"}
  world_arrows  = [["jp","us","<流れid>","pos|neg|mix","ラベル"], ...]
  moves         = [{"k":"inv|ord|ally|fund|exp|conf","a":"主語企業","b":"相手","path":["jp","us"],"t":"内容","amt":"金額","s":"<流れid>|null","note":"任意","date":"任意YYYY-MM-DD"}]
  streams_delta = {"<流れid>":{"phase":0-4,"why":"フェーズ判定の理由","ind":[["指標","値"]],"branch":"次の分岐点", ...}}
  co_meta       = {"企業名":{"c":"jp","ind":"業種","code":"証券コード","lens":"動きの見方1文"}}
"""
import json, os, html, datetime

esc = lambda s: html.escape(str(s))
PHASES = ["始動", "加速", "過熱", "選別・調整", "転換"]
KINDS = {"inv": ["出資・買収", "#2563eb"], "ord": ["受注・供給", "#16a34a"], "ally": ["提携・共同開発", "#7c3aed"],
         "fund": ["資金調達", "#0891b2"], "exp": ["進出・増産", "#ea580c"], "conf": ["対立・拒否", "#dc2626"]}

DEFAULT_STREAMS = [
 {"id": "ai", "name": "AI資本サイクル", "color": "#7c3aed", "flags": ["us", "jp", "tw", "kr"],
  "one": "巨大ITのAI投資が、半導体・電力・データセンターへお金を流し込んでいる。いまは「回収できるか」で選別が始まった段階。",
  "mech": ["ハイパースケーラーの巨額投資", "GPU・メモリー・装置の需要", "電力・DC建設の制約", "AI収益化で回収できるか"],
  "hist": "2000年のITバブルと、1990年代後半の通信網への過剰投資", "qs": ["aicapex", "aifin", "mem", "chips"], "kws": ["AI", "半導体", "データセンター", "GPU", "DRAM"]},
 {"id": "rate", "name": "金利・財政の正常化", "color": "#2563eb", "flags": ["jp", "us", "eu"],
  "one": "日本は「金利ある世界」へ戻る途中。国債費が増え、各国で財政の信認が問われ、為替と住宅・預金金利に波及する。",
  "mech": ["日銀の利上げ・物価2%", "長期金利の上昇", "国債費・予算の圧迫", "円・住宅ローン・預金"],
  "hist": "2006年の量的緩和解除と、1994年の米債券ショック", "qs": ["cb", "jgb", "fx", "tax", "banks"], "kws": ["金利", "日銀", "円", "国債", "財政", "税"]},
 {"id": "mideast", "name": "中東・エネルギー・資源", "color": "#ea580c", "flags": ["il", "ir", "sa", "au"],
  "one": "イランを巡る緊張が原油・LNGを押し上げ、日本の燃料・物流・物価に効いている。資源国と商社には追い風。",
  "mech": ["中東の軍事緊張", "原油・LNG・海運運賃の上昇", "航空・物流・電気代のコスト増", "物価と金利への波及"],
  "hist": "1973年の第1次石油危機と、1990年の湾岸危機", "qs": ["oil", "energytrans", "minerals"], "kws": ["原油", "LNG", "中東", "イラン", "原発", "資源"]},
 {"id": "bloc", "name": "米中対立とブロック化", "color": "#4f46e5", "flags": ["us", "cn", "jp"],
  "one": "関税・輸出規制・経済安保で世界がブロックに分かれつつある。サイバー攻撃も「見えない対立」の最前線になった。",
  "mech": ["米中の技術・通商対立", "関税・輸出規制・経済安保", "サプライチェーンの組み替え", "サイバー防御・国産化の需要"],
  "hist": "冷戦期の東西ブロック経済と、1930年代の保護主義", "qs": ["trade", "cyber", "sovai"], "kws": ["関税", "経済安保", "サイバー", "輸出規制"]},
 {"id": "china", "name": "中国の減速と輸出攻勢", "color": "#dc2626", "flags": ["cn", "th", "de"],
  "one": "国内の需要不足と過当競争で、中国企業がEVなどを海外へ押し出している。日本車の牙城・東南アジアや欧州が主戦場。",
  "mech": ["中国国内の需要不足・値下げ競争", "EV・電池・鉄鋼の輸出拡大", "東南アジア・欧州で価格競争", "日本企業の海外収益に圧力"],
  "hist": "1980年代の日米自動車摩擦（日本が「攻める側」だった）", "qs": ["china", "evchina"], "kws": ["中国", "BYD", "EV"]},
 {"id": "demo", "name": "人口減少と人手不足", "color": "#16a34a", "flags": ["jp", "kr"],
  "one": "日本は年齢の中央値が50歳を超えた。働き手不足が賃金・運賃・採用のルールを変え、値上げの新しい原因になっている。",
  "mech": ["少子高齢化・労働力の減少", "賃上げ・運賃上昇・採用改革", "企業コストの増加", "物価と暮らし方の変化"],
  "hist": "世界に先例がなく、日本が先頭を走る（韓国・中国が後を追う）", "qs": ["labor", "logi", "household"], "kws": ["賃金", "人手不足", "物流", "採用", "春闘", "介護"]},
 {"id": "sec", "name": "安全保障の再武装", "color": "#0f766e", "flags": ["jp", "us", "kp", "ru"],
  "one": "ロシア・北朝鮮・中国への備えで各国が防衛費を増やし、宇宙・AI・潜水艦まで領域が広がっている。",
  "mech": ["地政学リスクの高まり", "防衛費の増額・装備の高度化", "重工・電子・宇宙の受注", "財政負担と技術の波及"],
  "hist": "冷戦期の軍拡と、そこから生まれたインターネット・GPS", "qs": ["defense", "space"], "kws": ["防衛", "宇宙", "潜水艦", "ミサイル"]},
]
DEFAULT_LINKS = [["mideast", "rate", "原油高→インフレ→金利"], ["china", "bloc", "過剰輸出→関税・ブロック化"], ["bloc", "sec", "対立の激化→防衛費"],
                 ["ai", "mideast", "DC電力需要→エネルギー争奪"], ["demo", "ai", "人手不足→AI・自動化の需要"], ["sec", "rate", "防衛費→財政負担"]]


def _p(outdir, n): return os.path.join(outdir, n)
def _load(outdir, n, default):
    p = _p(outdir, n)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f: return json.load(f)
    return default
def _save(outdir, n, obj):
    with open(_p(outdir, n), "w", encoding="utf-8") as f: json.dump(obj, f, ensure_ascii=False, indent=1)


def flags_html(codes, h=13):
    out = []
    for c in codes or []:
        c = str(c).lower()
        out.append(f'<img src="flags/{esc(c)}.svg" alt="{esc(c)}" style="height:{h}px;width:auto;border-radius:2px;vertical-align:-2px;margin-right:2px;box-shadow:0 0 0 1px rgba(0,0,0,.1)">')
    return "".join(out)


def stream_meta(outdir):
    st = _load(outdir, "streams.json", None)
    return {s["id"]: s for s in (st or {"streams": DEFAULT_STREAMS})["streams"]}


def merge_world(d, outdir):
    date = d["date_iso"]
    st = _load(outdir, "streams.json", None)
    if not st:
        st = {"streams": json.loads(json.dumps(DEFAULT_STREAMS)), "links": DEFAULT_LINKS}
        for s in st["streams"]: s.update({"phase": 1, "phase_hist": [], "ind": [], "branch": ""})
    byid = {s["id"]: s for s in st["streams"]}
    for sid, v in (d.get("streams_delta") or {}).items():
        s = byid.get(sid)
        if not s: continue
        for k in ("one", "mech", "ind", "branch", "hist", "qs", "flags", "name", "color", "kws"):
            if k in v: s[k] = v[k]
        if "phase" in v:
            ph = int(v["phase"]); s["phase"] = ph
            hist = s.setdefault("phase_hist", [])
            hist[:] = [h for h in hist if h["date"] != date]
            if not hist or hist[-1]["phase"] != ph or v.get("why"):
                if not hist or hist[-1]["phase"] != ph:
                    hist.append({"date": date, "phase": ph, "why": v.get("why", "")})
                elif v.get("why") and not hist[-1].get("why"):
                    hist[-1]["why"] = v["why"]
    if d.get("stream_links"): st["links"] = d["stream_links"]
    _save(outdir, "streams.json", st)

    wn = [x for x in _load(outdir, "world_news.json", []) if x.get("date") != date]
    nadd = 0
    for i, n in enumerate(d.get("news", [])):
        w = n.get("world")
        if not w: continue
        wn.append({"date": date, "rank": i, "head": n["head"], "ind": n.get("ind", ""), "s": w.get("s"),
                   "c": [c.lower() for c in w.get("c", [])], "t": w.get("t", "mix"), "summ": n.get("summ", "")[:160]})
        nadd += 1
    wn.sort(key=lambda x: (x["date"], -x.get("rank", 0)))
    _save(outdir, "world_news.json", wn)

    wa = [x for x in _load(outdir, "world_arrows.json", []) if x.get("date") != date]
    for a in d.get("world_arrows", []):
        wa.append({"date": date, "f": a[0], "t": a[1], "s": a[2], "k": a[3], "l": a[4] if len(a) > 4 else ""})
    _save(outdir, "world_arrows.json", wa)

    mv = _load(outdir, "moves.json", [])
    madd = 0
    for m in d.get("moves", []):
        m = dict(m); m["date"] = m.get("date") or date
        m["path"] = [c.lower() for c in m.get("path", [])]
        if len(m["path"]) == 1: m["path"] = m["path"] * 2
        key = (m["date"], m["a"], m["b"], m["k"])
        mv = [x for x in mv if (x["date"], x["a"], x["b"], x["k"]) != key]
        mv.append(m); madd += 1
    mv.sort(key=lambda x: x["date"])
    _save(outdir, "moves.json", mv)

    cm = _load(outdir, "world_cos.json", {})
    for name, meta in (d.get("co_meta") or {}).items():
        cm.setdefault(name, {}).update(meta)
    for row in d.get("companies", []):
        name = row[0]
        e = cm.setdefault(name, {})
        e.setdefault("code", row[1]); e.setdefault("ind", row[2])
        e.setdefault("kk", {})[date] = row[4]
    _save(outdir, "world_cos.json", cm)
    return nadd, madd


def _recent(items, days, today):
    t = datetime.date.fromisoformat(today)
    return [x for x in items if (t - datetime.date.fromisoformat(x["date"])).days < days]


def index_teaser(outdir):
    st = _load(outdir, "streams.json", None)
    if not st: return ""
    wn = _load(outdir, "world_news.json", [])
    cards = []
    for s in st["streams"]:
        ev = [x for x in wn if x.get("s") == s["id"]]
        last = ev[-1] if ev else None
        lt = f'<div class="wt-ev">{flags_html(last["c"][:2], 11)}{esc(last["head"][:40])}{"…" if len(last["head"]) > 40 else ""}</div>' if last else ""
        ph = PHASES[s.get("phase", 1)]
        cards.append(f'<a class="wt-card" href="./world.html#s-{s["id"]}" style="border-top:3px solid {s["color"]}"><div class="wt-h"><span style="color:{s["color"]}">{esc(s["name"])}</span><span class="wt-ph" style="background:{s["color"]}">{ph}</span></div><div class="wt-f">{flags_html(s.get("flags", [])[:4], 12)}</div>{lt}</a>')
    css = ('<style>.wt-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px}.wt-card{display:block;background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:10px 12px;text-decoration:none;color:inherit}'
           '.wt-card:hover{box-shadow:0 2px 10px rgba(0,0,0,.08)}.wt-h{display:flex;justify-content:space-between;align-items:center;gap:6px;font-weight:700;font-size:14px}.wt-ph{color:#fff;font-size:11px;border-radius:8px;padding:0 7px;font-weight:600;white-space:nowrap}'
           '.wt-f{margin:5px 0}.wt-ev{font-size:12px;color:#475569;line-height:1.5}.wt-cta{display:inline-block;margin-top:12px;font-weight:700}</style>')
    return f'''<section id="world">{css}<h2><span class="num">🌐</span>世界の流れ（7本の潮流）</h2>
   <p class="lead">日々のニュースを7本の大きな流れに振り分け、世界地図で「どこで何が起き、どうつながっているか」を追います。企業どうしの出資・受注・提携も国をまたいで記録しています。</p>
   <div class="wt-grid">{"".join(cards)}</div><a class="wt-cta" href="./world.html">→ 世界地図で見る（流れ／企業のつながり）</a></section>'''


def render_world(outdir):
    st = _load(outdir, "streams.json", None)
    if not st: return 0
    wn = _load(outdir, "world_news.json", [])
    wa = _load(outdir, "world_arrows.json", [])
    mv = _load(outdir, "moves.json", [])
    cm = _load(outdir, "world_cos.json", {})
    stories = {}
    sp = _p(outdir, "stories.json")
    if os.path.exists(sp):
        for s in json.load(open(sp, encoding="utf-8")).get("stories", []): stories[s["id"]] = s.get("q", s["id"])
    dates = sorted({x["date"] for x in wn} | {x["date"] for x in mv})
    today = dates[-1] if dates else datetime.date.today().isoformat()
    names_in_moves = {}
    for m in mv:
        names_in_moves[m["a"]] = names_in_moves.get(m["a"], 0) + 1
        names_in_moves[m["b"]] = names_in_moves.get(m["b"], 0) + 1
    cos = {}
    for n, cnt in names_in_moves.items():
        meta = cm.get(n, {})
        c = meta.get("c")
        if not c:
            for m in mv:
                if m["a"] == n: c = m["path"][0]; break
                if m["b"] == n: c = m["path"][-1] if len(m["path"]) == 2 else m["path"][1]; break
        if meta.get("co") is False: continue
        if any((m["a"] == n and m.get("a_co") is False) or (m["b"] == n and m.get("b_co") is False) for m in mv): continue
        cos[n] = {"c": c, "ind": meta.get("ind", ""), "code": meta.get("code", ""), "lens": meta.get("lens", ""),
                  "kk": sorted((meta.get("kk") or {}).items()), "n": cnt}
    data = {"streams": st["streams"], "links": st.get("links", []), "news": _recent(wn, 30, today) if wn else [],
            "arrows": _recent(wa, 30, today) if wa else [], "moves": mv, "cos": cos, "today": today,
            "phases": PHASES, "kinds": KINDS, "stories": stories}
    js = json.dumps(data, ensure_ascii=False)
    body = WORLD_HTML.replace("/*DATA*/", "window.WD=" + js + ";").replace("{{TODAY}}", esc(today))
    with open(_p(outdir, "world.html"), "w", encoding="utf-8") as f: f.write(body)
    return len(mv)


WORLD_HTML = r'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>世界の流れ</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#1a1d23;--sub:#5b6270;--line:#e3e6eb;--land:#dfe3e8;--sea:#eef3f8;--pos:#16a34a;--neg:#dc2626;--mix:#9aa3ae;--landHi:#c4ccd6}
@media (prefers-color-scheme:dark){:root{--bg:#121418;--card:#1b1e24;--ink:#e8eaee;--sub:#9aa1ad;--line:#2c313a;--land:#2b3038;--sea:#171b21;--landHi:#3d4551;--mix:#6b7380}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,"Hiragino Sans","Noto Sans JP",sans-serif;line-height:1.6}
a{color:#2563eb}.wrap{max-width:1180px;margin:0 auto;padding:18px 16px 60px}
.home{font-size:13px;margin-bottom:6px}h1{font-size:22px;margin:0 0 2px}.lead{color:var(--sub);font-size:13px;margin:0 0 14px}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:10px}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:10px;overflow:hidden}.seg button{border:0;background:var(--card);color:var(--ink);padding:6px 12px;font-size:13px;cursor:pointer}.seg button.on{background:#334155;color:#fff}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 10px}.chip{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:16px;padding:4px 11px;font-size:12.5px;cursor:pointer;display:inline-flex;align-items:center;gap:6px}
.chip .dot{width:9px;height:9px;border-radius:50%}.chip.on{color:#fff;border-color:transparent}.chip.static{cursor:default}
.grid{display:grid;grid-template-columns:1fr 340px;gap:14px;align-items:start}@media(max-width:860px){.grid{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px}
svg{width:100%;height:auto;display:block}.ctry{fill:var(--land);stroke:var(--card);stroke-width:.5;vector-effect:non-scaling-stroke}.ctry.hit{cursor:pointer}.ctry.hit:hover{filter:brightness(.9)}
.sea{fill:var(--sea)}.grat{fill:none;stroke:var(--line);stroke-width:.4;vector-effect:non-scaling-stroke}
.arc{fill:none;opacity:.85;vector-effect:non-scaling-stroke}.archit{fill:none;stroke:transparent;stroke-width:14;cursor:pointer;vector-effect:non-scaling-stroke}.archit:hover+.lbl,.lbl.hit{cursor:pointer}#apop{position:fixed;z-index:50;max-width:340px;min-width:220px;background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:10px;box-shadow:0 8px 28px rgba(0,0,0,.25);padding:10px 12px;font-size:13px;display:none}#apop h4{margin:0 22px 6px 0;font-size:14px;display:flex;align-items:center;gap:4px;flex-wrap:wrap}#apop .x{position:absolute;right:8px;top:6px;border:0;background:none;font-size:18px;cursor:pointer;color:var(--ink)}#apop ul{list-style:none;margin:0;padding:0;max-height:260px;overflow:auto}#apop li{padding:5px 0;border-top:1px solid var(--line);line-height:1.45}#apop li:first-child{border-top:0}.lbl{paint-order:stroke;stroke:var(--card);fill:var(--ink);font-weight:600}
.pair{stroke-linecap:round;fill:none;cursor:pointer;opacity:.75;vector-effect:non-scaling-stroke}.pair.sel{opacity:1}.pairhit{stroke:transparent;fill:none;cursor:pointer;vector-effect:non-scaling-stroke;stroke-width:16}
.legend{display:flex;gap:12px;font-size:12px;color:var(--sub);margin-top:8px;flex-wrap:wrap}.legend i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:4px;vertical-align:-2px}
.flag{height:14px;width:auto;border-radius:2px;vertical-align:-2px;box-shadow:0 0 0 1px rgba(0,0,0,.1)}
.panel h3{margin:0 0 4px;font-size:16px;display:flex;align-items:center;gap:6px;flex-wrap:wrap}.panel ul{padding-left:0;list-style:none;margin:0}.panel li{padding:7px 0;border-bottom:1px solid var(--line);font-size:13px}
.tag{font-size:11px;padding:0 7px;border-radius:9px;color:#fff;margin-right:6px;white-space:nowrap;display:inline-block}.dt{font-size:11px;color:var(--sub);margin-right:5px}
.pairs{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}.pairs button{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;padding:4px 9px;font-size:12px;cursor:pointer}.pairs button.on{outline:2px solid #334155}
.mv{padding:9px 0;border-bottom:1px solid var(--line);font-size:13px}.mv .who{font-weight:600}.mv .amt{font-size:12px;color:var(--sub)}.mv .nt{font-size:11.5px;color:var(--sub);background:var(--bg);border-radius:6px;padding:3px 7px;margin-top:4px}
.co{color:inherit;text-decoration:underline dotted;cursor:pointer}.kd{display:inline-block;font-size:11px;padding:0 7px;border-radius:9px;color:#fff;margin-right:5px;white-space:nowrap}
h2{font-size:17px;margin:28px 0 10px}
.links{display:flex;flex-wrap:wrap;gap:8px}.link{font-size:12.5px;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:6px 10px}
.streams{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px}@media(max-width:400px){.streams{grid-template-columns:1fr}}
.st{border-top:4px solid}.st h3{margin:0;font-size:16px;display:flex;justify-content:space-between;align-items:center;gap:6px}
.one{font-size:13px;margin:6px 0 10px}.phase{display:flex;gap:3px;margin:4px 0 2px}.phase span{flex:1;font-size:10.5px;text-align:center;padding:3px 0;border-radius:4px;background:var(--line);color:var(--sub)}
.phase span.cur{color:#fff;font-weight:600}.phh{font-size:11.5px;color:var(--sub);margin-bottom:8px}
.mech{display:flex;flex-wrap:wrap;align-items:center;gap:4px;font-size:12px;margin-bottom:6px}.mech b{font-weight:500;background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:2px 7px}.mech em{font-style:normal;color:var(--sub)}
.sec{font-size:11.5px;color:var(--sub);margin:9px 0 3px;font-weight:600}.ind{font-size:12.5px;display:grid;grid-template-columns:auto 1fr;gap:2px 10px}.ind div:nth-child(odd){color:var(--sub)}
.ev{font-size:12.5px;margin:0;padding:0;list-style:none}.ev li{margin:3px 0;display:flex;gap:6px;align-items:flex-start}.ev .flag{margin-top:3px}
.kv{font-size:12.5px}.qs{display:flex;flex-wrap:wrap;gap:5px}.qs a{font-size:11.5px;border:1px solid var(--line);border-radius:10px;padding:1px 8px;text-decoration:none;color:var(--ink)}
.cohead{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.cohead h3{margin:0;font-size:18px}.cogrid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:10px}@media(max-width:760px){.cogrid{grid-template-columns:1fr}}
.lens{background:var(--bg);border-left:3px solid #334155;padding:8px 10px;font-size:13px;margin-top:10px;border-radius:4px}
.tl{list-style:none;margin:0;padding:0;border-left:2px solid var(--line);margin-left:6px}.tl li{position:relative;padding:4px 0 10px 16px;font-size:13px}.tl li:before{content:"";position:absolute;left:-6px;top:9px;width:10px;height:10px;border-radius:50%;background:var(--c)}
#ego{max-width:420px;margin:0 auto}#ego text{font-size:11.5px;fill:var(--ink);paint-order:stroke;stroke:var(--card);stroke-width:3px}
.search{border:1px solid var(--line);border-radius:8px;padding:5px 10px;font-size:13px;background:var(--card);color:var(--ink);min-width:180px}
.news{list-style:none;padding:0;margin:0}.news li{display:flex;gap:8px;align-items:center;padding:8px 0;border-bottom:1px solid var(--line);font-size:13.5px;flex-wrap:wrap}.ind2{font-size:11px;color:var(--sub);min-width:62px}
.note{font-size:12px;color:var(--sub);margin-top:24px}
</style></head><body><div class="wrap">
<div class="home"><a href="./index.html">← ダッシュボードへ戻る</a></div>
<h1>🌐 世界の流れ</h1>
<p class="lead">日々のニュースを7本の大きな流れに振り分け、世界のどこで何が起き、どうつながっているかを地図で見ます。最新：{{TODAY}}</p>
<div class="bar"><div class="seg" id="mode"><button data-m="flow">🌐 流れで見る</button><button data-m="co">🏢 企業のつながりで見る</button></div>
<div class="seg" id="win"><button data-w="1">きょう</button><button data-w="7">7日</button><button data-w="30">30日</button></div>
<div class="seg" id="zoom"><button data-z="world">世界</button><button data-z="asia">東アジア</button><button data-z="eu">欧州・中東</button><button data-z="am">米州</button></div></div>
<div class="chips" id="chips"></div><div class="chips" id="kinds" style="display:none"></div>
<div class="grid"><div class="card"><svg id="map"></svg><div class="legend" id="legend"></div><div class="pairs" id="pairs"></div></div><div class="card panel" id="panel"></div></div>
<h2 id="coh">🏢 企業の動き</h2><div class="bar"><input class="search" id="cosearch" placeholder="企業名で絞り込み"></div><div class="chips" id="cochips"></div><div class="card" id="cocard"></div>
<h2>流れどうしのつながり</h2><div class="links" id="links"></div>
<h2>7つの流れ</h2><div class="streams" id="streams"></div>
<h2>きょうのニュース</h2><div class="card"><ul class="news" id="news"></ul></div>
<p class="note">流れ・国・企業の動きは各日のニュース記事に書かれた事実から振り分けています。フェーズは日々の判定で、変化した日と理由を履歴に残します。</p>
</div>
<script src="assets/world_map.js"></script><script>/*DATA*/</script>
<script>
const M=window.WMAP,D=window.WD,NS="http://www.w3.org/2000/svg";const S=Object.fromEntries(D.streams.map(s=>[s.id,s]));
let mode=(location.hash==="#co")?"co":"flow",win=1,zoom="world",cur="all",selC=null,selPair=null,selCo=null,coq="";
const ZM={world:[0,0,M.W,M.H],asia:[300,62,250,123],eu:[110,48,250,123],am:[560,30,400,197]};
const F=(c,h)=>c?`<img class="flag" src="flags/${c}.svg" alt="" style="${h?'height:'+h+'px':''}">`:"";
const NM=c=>(M.names&&M.names[c])||c;const col=k=>({pos:"var(--pos)",neg:"var(--neg)",mix:"var(--mix)"}[k]||"var(--mix)");
const svg=document.getElementById('map');
const dd=s=>{const t=new Date(D.today),x=new Date(s);return Math.round((t-x)/864e5)};
const inWin=x=>dd(x.date)<win;const md=s=>{const p=s.split("-");return (+p[1])+"/"+(+p[2])};
function el(t,a,p){const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);(p||svg).appendChild(e);return e}
function base(){svg.innerHTML="";const z=ZM[zoom];svg.setAttribute('viewBox',z.join(" "));el('path',{d:M.sphere,class:'sea'});el('path',{d:M.grat,class:'grat'});return M.W/z[2]}
function curve(A,B,i){i=i||0;const L=Math.hypot(B[0]-A[0],B[1]-A[1]);const mx=(A[0]+B[0])/2,my=(A[1]+B[1])/2-Math.max(14+i*10,L*(.18+i*.09));return [`M${A[0]},${A[1]} Q${mx},${my} ${B[0]},${B[1]}`,(A[0]+2*mx+B[0])/4,(A[1]+2*my+B[1])/4,mx,my]}
function placeLbl(t,placed,zf){let b=t.getBBox();const pad=2/zf;const hit=r=>placed.some(q=>r.x<q.x+q.width+pad&&r.x+r.width+pad>q.x&&r.y<q.y+q.height+pad&&r.y+r.height+pad>q.y);const y0=+t.getAttribute('y');let k=0;while(hit(b)&&k<12){k++;const dy=Math.ceil(k/2)*(b.height+pad)*(k%2?1:-1);t.setAttribute('y',y0+dy);b=t.getBBox()}placed.push(b)}
function newsWin(){return D.news.filter(inWin)}
function cItems(c){return newsWin().filter(n=>n.c.includes(c)&&(cur==="all"||n.s===cur))}
function tone(items){const n=k=>items.filter(x=>x.t===k).length;return n('pos')>n('neg')?'pos':n('neg')>n('pos')?'neg':'mix'}
function openPop(its,ev){let p=document.getElementById('apop');if(!p){p=document.createElement('div');p.id='apop';document.body.appendChild(p);document.addEventListener('click',e=>{if(!p.contains(e.target))p.style.display='none'});document.addEventListener('keydown',e=>{if(e.key==='Escape')p.style.display='none'})}
 const a=its[0],st=S[a.s];p.innerHTML=`<button class="x" aria-label="閉じる">×</button><h4>${F(a.f,14)}${NM(a.f)} → ${F(a.t,14)}${NM(a.t)}</h4><div class="dt" style="margin-bottom:6px"><span class="tag" style="background:${st.color}">${st.name}</span> ${win===1?'きょう':'直近'+win+'日'}・${its.length}件</div><ul>${its.map(x=>`<li><span class="dt">${md(x.date)}</span> <span style="color:${col(x.k)}">●</span> ${x.l||'（ラベルなし）'}</li>`).join('')}</ul>`;
 p.querySelector('.x').onclick=()=>{p.style.display='none'};p.style.display='block';const w=p.offsetWidth,hh=p.offsetHeight;let x=ev.clientX+12,y=ev.clientY+12;if(x+w>innerWidth-8)x=Math.max(8,ev.clientX-w-12);if(y+hh>innerHeight-8)y=Math.max(8,innerHeight-hh-8);p.style.left=x+'px';p.style.top=y+'px'}
function drawFlow(){const zf=base();const act={};for(const n of newsWin()){if(cur!=="all"&&n.s!==cur)continue;n.c.forEach(c=>{(act[c]=act[c]||[]).push(n)})}
 if(!selC||!act[selC])selC=act.jp?"jp":Object.keys(act)[0]||null;
 for(const c of M.countries){const p=el('path',{d:c.d,class:'ctry'});if(c.iso&&act[c.iso]){p.style.fill=col(tone(act[c.iso]));p.style.opacity=c.iso===selC?1:.7;p.classList.add('hit');p.onclick=()=>{selC=c.iso;render()}}const t=el('title',{},p);t.textContent=NM(c.iso)}
 const defs=el('defs',{});["pos","neg","mix"].forEach(k=>{const m=el('marker',{id:'h'+k,viewBox:'0 0 10 10',refX:8,refY:5,markerUnits:'userSpaceOnUse',markerWidth:11/zf,markerHeight:11/zf,orient:'auto'},defs);el('path',{d:'M0,0L10,5L0,10z',fill:getComputedStyle(document.documentElement).getPropertyValue('--'+k)},m)});
 const G={};for(const a of D.arrows.filter(inWin)){if(cur!=="all"&&a.s!==cur)continue;if(!M.cent[a.f]||!M.cent[a.t]||!S[a.s])continue;const g=a.f+'>'+a.t+'>'+a.s;(G[g]=G[g]||[]).push(a)}
 const pc={},placed=[],lbls=[];for(const g in G){const its=G[g].slice().sort((x,y)=>x.date<y.date?1:-1),a=its[0],n=its.length;const A=M.cent[a.f],B=M.cent[a.t];const pkey=[a.f,a.t].sort().join('|');const pi=pc[pkey]=(pc[pkey]===undefined?0:pc[pkey]+1);const [d,mx,my,qx,qy]=curve(A,B,pi);
  const cnt={};its.forEach(x=>cnt[x.k]=(cnt[x.k]||0)+1);const k=Object.keys(cnt).sort((x,y)=>cnt[y]-cnt[x])[0];
  el('path',{d,class:'arc',stroke:S[a.s].color,'stroke-width':2.2+Math.min(n-1,4)*.7,'marker-end':`url(#h${k})`});const h=el('path',{d,class:'archit'});h.onclick=ev=>{ev.stopPropagation();openPop(its,ev)};const tt=el('title',{},h);tt.textContent=`${NM(a.f)}→${NM(a.t)}（${n}件）クリックで一覧`;
  if(cur!=="all"&&a.l)lbls.push([a.l+(n>1?` ほか${n-1}件`:''),A,B,qx,qy,its])}
 const Z=ZM[zoom],mg=Z[2]*.06;const inV=(x,y)=>x>Z[0]+mg&&x<Z[0]+Z[2]-mg&&y>Z[1]+mg*.6&&y<Z[1]+Z[3]-mg*.6;
 for(const [l,A,B,qx,qy,its] of lbls){let mx=null,my=null;for(const t0 of [.5,.45,.55,.4,.6,.35,.65,.3,.7,.25,.75,.2,.8,.15,.85,.1,.9]){const u=1-t0,x=u*u*A[0]+2*u*t0*qx+t0*t0*B[0],y=u*u*A[1]+2*u*t0*qy+t0*t0*B[1];if(inV(x,y)){mx=x;my=y;break}}if(mx===null)continue;const t=el('text',{x:mx,y:my,'text-anchor':'middle',class:'lbl','font-size':12/zf,'stroke-width':3/zf});t.textContent=l;t.classList.add('hit');t.onclick=ev=>{ev.stopPropagation();openPop(its,ev)};{const b=t.getBBox(),r=Z[0]+Z[2]-4/zf,lf=Z[0]+4/zf;if(b.x+b.width>r)t.setAttribute('x',mx-(b.x+b.width-r));else if(b.x<lf)t.setAttribute('x',mx+(lf-b.x))}placeLbl(t,placed,zf)}
 for(const c in act){const C=M.cent[c];if(C)el('image',{href:`flags/${c}.svg`,x:C[0]-8/zf,y:C[1]-6/zf,width:16/zf,height:12/zf})}
 document.getElementById('legend').innerHTML='<span><i style="background:var(--pos)"></i>追い風</span><span><i style="background:var(--neg)"></i>逆風・緊張</span><span><i style="background:var(--mix)"></i>まちまち</span><span>矢印＝お金・モノ・リスクの流れ（太さ＝件数、流れを選ぶとラベル表示、矢印を押すと一覧）</span>';
 document.getElementById('pairs').innerHTML="";
 const p=document.getElementById('panel');if(!selC){p.innerHTML='<h3>この期間・流れのニュースはありません</h3>';return}
 const its=cItems(selC).slice().reverse();p.innerHTML=`<h3>${F(selC,16)}${NM(selC)}</h3><div class="dt">${cur==="all"?"すべての流れ":S[cur].name}・${win===1?"きょう":"直近"+win+"日"}・${its.length}件</div><ul>${its.map(x=>`<li><span class="dt">${md(x.date)}</span>${S[x.s]?`<span class="tag" style="background:${S[x.s].color}">${S[x.s].name}</span>`:""}<span style="color:${col(x.t)}">●</span> ${x.head}</li>`).join("")}</ul><div class="dt" style="margin-top:8px">色の付いた国を押すと切り替わります</div>`}
const pk=(a,b)=>[a,b].sort().join("|");
function agg(){const P={},Dm={};for(const m of D.moves.filter(inWin)){if(m.path[0]===m.path[1]){(Dm[m.path[0]]=Dm[m.path[0]]||[]).push(m);continue}for(let i=0;i<m.path.length-1;i++){if(m.path[i]===m.path[i+1])continue;const k=pk(m.path[i],m.path[i+1]);(P[k]=P[k]||[]).push(m)}}return {P,Dm}}
function drawCo(){const zf=base();const {P,Dm}=agg();const inv=new Set();Object.keys(P).forEach(k=>k.split("|").forEach(c=>inv.add(c)));Object.keys(Dm).forEach(c=>inv.add(c));
 const keys=Object.keys(P).sort((a,b)=>P[b].length-P[a].length).concat(Object.keys(Dm).map(c=>"dom:"+c));
 if(!selPair||!(selPair in P||selPair.startsWith("dom:")&&Dm[selPair.slice(4)]))selPair=keys[0]||null;
 for(const c of M.countries){const p=el('path',{d:c.d,class:'ctry'});if(c.iso&&inv.has(c.iso))p.style.fill='var(--landHi)';const t=el('title',{},p);t.textContent=NM(c.iso)}
 for(const k in P){const [a,b]=k.split("|");const A=M.cent[a],B=M.cent[b];if(!A||!B)continue;const ms=P[k];const cnt={};ms.forEach(m=>cnt[m.k]=(cnt[m.k]||0)+1);const dk=Object.keys(cnt).sort((x,y)=>cnt[y]-cnt[x])[0];
  const [d,mx,my]=curve(A,B);el('path',{d,class:'pair'+(selPair===k?' sel':''),stroke:D.kinds[dk][1],'stroke-width':1.5+Math.min(ms.length,8)*1.4});const h=el('path',{d,class:'pairhit'});h.onclick=()=>{selPair=k;render()};
  const g=el('g',{style:'cursor:pointer'});el('circle',{cx:mx,cy:my,r:9/zf,fill:'var(--card)',stroke:D.kinds[dk][1],'stroke-width':1.5/zf},g);const tx=el('text',{x:mx,y:my+4/zf,'text-anchor':'middle','font-size':11/zf,'font-weight':700,fill:'var(--ink)'},g);tx.textContent=ms.length;g.onclick=()=>{selPair=k;render()}}
 for(const c in Dm){const C=M.cent[c];if(!C)continue;const g=el('g',{style:'cursor:pointer'});el('circle',{cx:C[0]+14/zf,cy:C[1]+11/zf,r:10/zf,fill:'#334155',stroke:selPair==='dom:'+c?'#fbbf24':'none','stroke-width':2/zf},g);const tx=el('text',{x:C[0]+14/zf,y:C[1]+15/zf,'text-anchor':'middle','font-size':11/zf,'font-weight':700,fill:'#fff'},g);tx.textContent=Dm[c].length;const tt=el('title',{},g);tt.textContent=NM(c)+'の国内の企業どうしの動き';g.onclick=()=>{selPair='dom:'+c;render()}}
 for(const c of inv){const C=M.cent[c];if(C)el('image',{href:`flags/${c}.svg`,x:C[0]-8/zf,y:C[1]-6/zf,width:16/zf,height:12/zf})}
 document.getElementById('legend').innerHTML='<span>線の色＝動きの種類／太さ・数字＝件数／紺の丸＝国内どうしの件数</span>';
 const lab=k=>k.startsWith("dom:")?`${F(k.slice(4))}${NM(k.slice(4))}国内`:k.split("|").map(c=>F(c)+NM(c)).join(" ⇄ ");
 document.getElementById('pairs').innerHTML=keys.map(k=>`<button class="${k===selPair?'on':''}" data-k="${k}">${lab(k)} <b>${k.startsWith("dom:")?Dm[k.slice(4)].length:P[k].length}</b></button>`).join("");
 document.querySelectorAll('#pairs button').forEach(b=>b.onclick=()=>{selPair=b.dataset.k;render()});
 const ms=!selPair?[]:selPair.startsWith("dom:")?Dm[selPair.slice(4)]:P[selPair];
 document.getElementById('panel').innerHTML=!selPair?'<h3>この期間の企業の動きはありません</h3><div class="dt">期間を「30日」に広げてください</div>':`<h3>${lab(selPair)}</h3><div class="dt">${ms.length}件・${win===1?"きょう":"直近"+win+"日"}</div>`+ms.slice().reverse().map(m=>`<div class="mv"><span class="kd" style="background:${D.kinds[m.k][1]}">${D.kinds[m.k][0]}</span><span class="who">${coLink(m.a)} → ${coLink(m.b)}</span><div>${m.t}</div><div class="amt">${md(m.date)}　${m.amt&&m.amt!=='—'?'金額：'+m.amt:''}${S[m.s]?' <span class="tag" style="background:'+S[m.s].color+'">'+S[m.s].name+'</span>':''}</div>${m.note?'<div class="nt">🧭 '+m.note+'</div>':''}</div>`).join("");
 bindCo()}
const coLink=n=>D.cos[n]?`<a class="co" data-co="${n}">${n}</a>`:n;
function bindCo(){document.querySelectorAll('[data-co]').forEach(a=>a.onclick=()=>{selCo=a.dataset.co;coSection();document.getElementById('coh').scrollIntoView({behavior:'smooth'})})}
function coSection(){const names=Object.keys(D.cos).filter(n=>!coq||n.includes(coq)).sort((a,b)=>D.cos[b].n-D.cos[a].n||a.localeCompare(b));
 if(!selCo||!D.cos[selCo])selCo=names[0];document.getElementById('cochips').innerHTML=names.slice(0,40).map(n=>`<button class="chip ${n===selCo?'on':''}" style="${n===selCo?'background:#334155':''}" data-co="${n}">${F(D.cos[n].c)}${n}<span class="dt">${D.cos[n].n}</span></button>`).join("");
 const c=D.cos[selCo];if(!c){document.getElementById('cocard').innerHTML='該当なし';return}
 const rel=D.moves.filter(m=>m.a===selCo||m.b===selCo);
 const tl=rel.map(m=>({d:m.date,k:m.k,t:(m.a===selCo?'→ '+m.b:'← '+m.a)+'：'+m.t})).concat(c.kk.map(([d,t])=>({d,k:'kk',t}))).sort((a,b)=>b.d.localeCompare(a.d));
 const KK=Object.assign({},D.kinds,{kk:["その日の動き","#64748b"]});
 const cps=rel.map(m=>{const out=m.a===selCo;return {n:out?m.b:m.a,c:out?m.path[1]:m.path[0],k:m.k}});
 const W=380,H=270,cx=W/2,cy=H/2;let ego=`<svg id="ego" viewBox="0 0 ${W} ${H}">`;cps.forEach((p,i)=>{const an=-Math.PI/2+i*2*Math.PI/Math.max(cps.length,1);const x=cx+Math.cos(an)*125,y=cy+Math.sin(an)*95;
  ego+=`<line x1="${cx}" y1="${cy}" x2="${x}" y2="${y}" stroke="${D.kinds[p.k][1]}" stroke-width="2.5"/><circle cx="${x}" cy="${y}" r="5" fill="${D.kinds[p.k][1]}"/>${p.c?`<image href="flags/${p.c}.svg" x="${x-8}" y="${y+7}" width="16" height="12"/>`:''}<text x="${x}" y="${y-9}" text-anchor="middle">${p.n.length>14?p.n.slice(0,14)+'…':p.n}</text>`});
 ego+=`<circle cx="${cx}" cy="${cy}" r="32" fill="#334155"/><text x="${cx}" y="${cy+4}" text-anchor="middle" style="fill:#fff;stroke:none;font-weight:700">${selCo.length>7?selCo.slice(0,6)+'…':selCo}</text></svg>`;
 document.getElementById('cocard').innerHTML=`<div class="cohead">${F(c.c,18)}<h3>${selCo}</h3><span class="dt">${c.ind||""}${c.code&&c.code!=="—"?"・"+c.code:""}</span></div>${c.lens?`<div class="lens">💡 この会社の動きの見方：${c.lens}</div>`:""}
 <div class="cogrid"><div><div class="sec">動きのタイムライン（新しい順）</div><ul class="tl">${tl.map(x=>`<li style="--c:${KK[x.k][1]}"><span class="dt">${md(x.d)}</span><span class="kd" style="background:${KK[x.k][1]}">${KK[x.k][0]}</span>${x.t}</li>`).join("")}</ul></div>
 <div><div class="sec">つながり（線の色＝動きの種類）</div>${cps.length?ego:'<div class="dt">まだ企業どうしの動きの記録がありません</div>'}</div></div>`;bindCo()}
function chips(){const e=document.getElementById('chips');e.style.display=mode==='flow'?'flex':'none';document.getElementById('kinds').style.display=mode==='co'?'flex':'none';
 e.innerHTML=[`<button class="chip ${cur==='all'?'on':''}" style="${cur==='all'?'background:#334155':''}" data-id="all">すべて</button>`].concat(D.streams.map(s=>`<button class="chip ${cur===s.id?'on':''}" style="${cur===s.id?'background:'+s.color:''}" data-id="${s.id}"><span class="dot" style="background:${cur===s.id?'#fff':s.color}"></span>${s.name}</button>`)).join("");
 e.querySelectorAll('button').forEach(b=>b.onclick=()=>{cur=b.dataset.id;selC=null;render()});
 document.getElementById('kinds').innerHTML=Object.values(D.kinds).map(k=>`<span class="chip static"><span class="dot" style="background:${k[1]}"></span>${k[0]}</span>`).join("")}
function segs(){[["mode","m",mode],["win","w",String(win)],["zoom","z",zoom]].forEach(([id,a,v])=>document.querySelectorAll('#'+id+' button').forEach(b=>b.classList.toggle('on',b.dataset[a]===v)))}
function render(){const _p=document.getElementById('apop');if(_p)_p.style.display='none';segs();chips();mode==='flow'?drawFlow():drawCo()}
document.querySelectorAll('#mode button').forEach(b=>b.onclick=()=>{mode=b.dataset.m;render()});
document.querySelectorAll('#win button').forEach(b=>b.onclick=()=>{win=+b.dataset.w;selPair=null;render()});
document.querySelectorAll('#zoom button').forEach(b=>b.onclick=()=>{zoom=b.dataset.z;render()});
document.getElementById('cosearch').oninput=e=>{coq=e.target.value.trim();coSection()};
document.getElementById('links').innerHTML=D.links.filter(l=>S[l[0]]&&S[l[1]]).map(l=>`<span class="link"><b style="color:${S[l[0]].color}">${S[l[0]].name}</b> → <b style="color:${S[l[1]].color}">${S[l[1]].name}</b><br><span style="color:var(--sub)">${l[2]}</span></span>`).join("");
document.getElementById('streams').innerHTML=D.streams.map(s=>{const ev=D.news.filter(n=>n.s===s.id).slice(-5).reverse();const ph=s.phase_hist||[];
 return `<div class="card st" id="s-${s.id}" style="border-top-color:${s.color}"><h3>${s.name}<span>${(s.flags||[]).map(c=>F(c)).join(" ")}</span></h3><p class="one">${s.one}</p>
<div class="sec">いまのフェーズ</div><div class="phase">${D.phases.map((p,i)=>`<span class="${i===s.phase?'cur':''}" style="${i===s.phase?'background:'+s.color:''}">${p}</span>`).join("")}</div>
<div class="phh">${ph.length?ph.slice(-3).reverse().map(h=>`${md(h.date)}：${D.phases[h.phase]}${h.why?"（"+h.why+"）":""}`).join("<br>"):""}</div>
<div class="sec">仕組み</div><div class="mech">${s.mech.map(m=>`<b>${m}</b>`).join("<em>→</em>")}</div>
${(s.ind||[]).length?`<div class="sec">定点指標</div><div class="ind">${s.ind.map(i=>`<div>${i[0]}</div><div>${i[1]}</div>`).join("")}</div>`:""}
<div class="sec">最近の出来事</div><ul class="ev">${ev.length?ev.map(e=>`<li>${e.c.slice(0,2).map(c=>F(c)).join("")}<span><span class="dt">${md(e.date)}</span>${e.head}</span></li>`).join(""):'<li class="dt">直近30日の記録なし</li>'}</ul>
${s.branch?`<div class="sec">次の分岐点</div><div class="kv">${s.branch}</div>`:""}<div class="sec">歴史上の似た局面</div><div class="kv">${s.hist}</div>
<div class="sec">関連する問い</div><div class="qs">${(s.qs||[]).map(q=>`<a href="./deepdives.html">${D.stories[q]||q}</a>`).join("")}</div></div>`}).join("");
document.getElementById('news').innerHTML=D.news.filter(n=>n.date===D.today).sort((a,b)=>a.rank-b.rank).map(n=>`<li>${n.c.map(c=>F(c)).join("")}<span class="ind2">${n.ind}</span><span style="flex:1;min-width:200px">${n.head}</span>${S[n.s]?`<span class="tag" style="background:${S[n.s].color}">${S[n.s].name}</span>`:""}</li>`).join("");
if(location.hash.startsWith("#s-")){setTimeout(()=>document.querySelector(location.hash)?.scrollIntoView(),50)}
render();coSection();
</script></body></html>'''
