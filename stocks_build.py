# -*- coding: utf-8 -*-
"""株価×ニュース：ニュースと株価の動きを結びつけて蓄積・描画する。
build_digest.py から呼ばれる:
  merge_stocks(day_data, outdir) -> stocks.json を更新（終値の蓄積・見立ての履歴）
  render_stocks(outdir)          -> stocks.html を生成
  digest_block(day_data, outdir) -> 日次HTMLに差し込む「株価の反応」セクション
  index_teaser(outdir)           -> index.html 用の短いブロック
day_data.json の追加フィールド（任意）:
  stocks = {
    "px":    {"7203": [["2026-11-11", 3435], ...], "1321": [...]},     # 国内：日経会社情報の時系列（終値）。1321=日経平均連動ETF（比較の基準）
    "us":    {"NVDA": [["2026-11-11", 173.73, 2.86]]},                   # 海外：終値と前日比%
    "views": [{"code":"6989","name":"北陸電気工業","tone":"pos|neg|mix","news":"関連ニュース（短く）",
               "drivers":"株価を動かしている要因","outlook":"今後の見立て","up":"上振れシナリオ（トリガー）",
               "down":"下振れシナリオ（トリガー）","watch":"次の注目イベント（日付）"}],
    "market":{"view":"相場全体の見立て","watch":["注目イベント", ...]}
  }
"""
import json, os, html, datetime, re

esc = lambda s: html.escape(str(s))
BENCH = "1321"
JP = re.compile(r"^\d{3}[0-9A-Z]$")


def _p(o, n): return os.path.join(o, n)
def _load(o, n, d):
    p = _p(o, n)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f: return json.load(f)
    return d
def _save(o, n, obj):
    with open(_p(o, n), "w", encoding="utf-8") as f: json.dump(obj, f, ensure_ascii=False, indent=1)


def merge_stocks(d, outdir):
    st = _load(outdir, "stocks.json", {"bench": BENCH, "names": {}, "px": {}, "chg": {}, "views": {}, "market": []})
    S = d.get("stocks") or {}
    date = d["date_iso"]
    npx = 0
    for code, rows in (S.get("px") or {}).items():
        m = st["px"].setdefault(code, {})
        for r in rows:
            if r[1] is None: continue
            m[r[0]] = float(r[1]); npx += 1
    for code, rows in (S.get("us") or {}).items():
        m = st["px"].setdefault(code, {}); c = st["chg"].setdefault(code, {})
        for r in rows:
            m[r[0]] = float(r[1])
            if len(r) > 2 and r[2] is not None: c[r[0]] = float(r[2])
        st["names"].setdefault(code, {}).setdefault("mkt", "us")
    cos = _load(outdir, "world_cos.json", {})
    for name, meta in cos.items():
        cd = str(meta.get("code", ""))
        if cd in st["px"]:
            e = st["names"].setdefault(cd, {})
            e.setdefault("name", name); e.setdefault("ind", meta.get("ind", ""))
    for row in d.get("companies", []):
        cd = str(row[1])
        if cd in st["px"]:
            e = st["names"].setdefault(cd, {}); e["name"] = row[0]; e.setdefault("ind", row[2])
    nv = 0
    for v in S.get("views", []) or []:
        cd = str(v.get("code", ""))
        if not cd: continue
        e = st["names"].setdefault(cd, {})
        if v.get("name"): e["name"] = v["name"]
        if v.get("ind"): e["ind"] = v["ind"]
        L = st["views"].setdefault(cd, [])
        L[:] = [x for x in L if x["date"] != date]
        x = {k: v.get(k, "") for k in ("tone", "news", "drivers", "outlook", "up", "down", "watch")}
        x["date"] = date; L.append(x); L.sort(key=lambda z: z["date"]); nv += 1
    if S.get("market"):
        st["market"] = [x for x in st.get("market", []) if x["date"] != date] + [dict(S["market"], date=date)]
    st["names"].setdefault(BENCH, {"name": "日経平均連動ETF（1321）", "ind": "指数"})
    _save(outdir, "stocks.json", st)
    return npx, nv


# ---------- 計算 ----------
def _series(st, code):
    m = st["px"].get(code, {})
    return sorted(m.items())


def _ret(ser, i, k):
    if i - k < 0 or i >= len(ser): return None
    a, b = ser[i - k][1], ser[i][1]
    return (b / a - 1) * 100 if a else None


def _react(st, code, date):
    """date（紙面の日付）以降の最初の取引日の反応。戻り値: dict or None"""
    ser = _series(st, code)
    if len(ser) < 2: return None
    idx = next((i for i, (dt, _) in enumerate(ser) if dt >= date), None)
    us = st["names"].get(code, {}).get("mkt") == "us"
    if idx is None: return None
    t0 = ser[idx][0]
    if (datetime.date.fromisoformat(t0) - datetime.date.fromisoformat(date)).days > 5: return None
    r1 = _ret(ser, idx, 1)
    if r1 is None and us: r1 = st["chg"].get(code, {}).get(t0)
    if r1 is None: return None
    b1 = None; ex = None
    if not us:
        bs = _series(st, BENCH); bi = next((i for i, (dt, _) in enumerate(bs) if dt == t0), None)
        if bi is not None and bi > 0:
            b1 = _ret(bs, bi, 1); ex = r1 - b1 if b1 is not None else None
    r5 = None
    if idx + 4 < len(ser) and idx >= 1: r5 = (ser[idx + 4][1] / ser[idx - 1][1] - 1) * 100
    return {"t0": t0, "r1": r1, "b1": b1, "ex": ex, "r5": r5}


def _label(tone, rr):
    if not rr: return ("データなし", "#94a3b8")
    x = rr["ex"] if rr["ex"] is not None else rr["r1"]
    if abs(x) < 1.0: return ("反応薄", "#94a3b8")
    if tone == "pos": return ("好感", "#16a34a") if x > 0 else ("材料出尽くし・逆行安", "#d97706")
    if tone == "neg": return ("失望・売り", "#dc2626") if x < 0 else ("悪材料でも逆行高", "#7c3aed")
    return ("買われる", "#16a34a") if x > 0 else ("売られる", "#dc2626")


def _events(st, cos):
    """code -> [(date, text, tone)]"""
    ev = {}
    for name, meta in cos.items():
        cd = str(meta.get("code", ""))
        if cd not in st["px"]: continue
        for dt, txt in (meta.get("kk") or {}).items():
            ev.setdefault(cd, {})[dt] = [txt, "mix"]
    for cd, L in st.get("views", {}).items():
        for v in L:
            e = ev.setdefault(cd, {}).setdefault(v["date"], [v.get("news") or "", v.get("tone") or "mix"])
            if v.get("news"): e[0] = v["news"]
            e[1] = v.get("tone") or e[1]
    return {cd: sorted((dt, t, tn) for dt, (t, tn) in m.items()) for cd, m in ev.items()}


def _fmt(x, d=1):
    if x is None: return "—"
    if abs(x) < 0.05: return "±0.0%"
    return f'{"+" if x > 0 else ""}{x:.{d}f}%'


def _cls(x): return "" if x is None else ("up" if x > 0 else ("dn" if x < 0 else ""))


def _chart(st, code, evs, w=320, h=96, n=30):
    ser = _series(st, code)[-n:]
    if len(ser) < 2: return '<div class="nochart">株価データの蓄積待ち</div>'
    bs = dict(_series(st, BENCH)) if st["names"].get(code, {}).get("mkt") != "us" else {}
    vals = [v for _, v in ser]
    base = vals[0]; bb = bs.get(ser[0][0])
    rel = [(v / base - 1) * 100 for v in vals]
    brel = [((bs[d] / bb - 1) * 100) if (bb and d in bs) else None for d, _ in ser]
    allv = rel + [x for x in brel if x is not None]
    lo, hi = min(allv), max(allv)
    if hi - lo < 2: hi += 1; lo -= 1
    X = lambda i: 6 + i * (w - 12) / (len(ser) - 1)
    Y = lambda v: 6 + (hi - v) * (h - 18) / (hi - lo)
    pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(rel))
    bpts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(brel) if v is not None)
    col = "#16a34a" if rel[-1] >= 0 else "#dc2626"
    dots = []
    dates = [d for d, _ in ser]
    for dt, txt, tone in evs:
        idx = next((i for i, d in enumerate(dates) if d >= dt), None)
        if idx is None: continue
        rr = _react(st, code, dt); lab, lc = _label(tone, rr)
        dots.append(f'<circle cx="{X(idx):.1f}" cy="{Y(rel[idx]):.1f}" r="4.5" fill="{lc}" stroke="var(--card)" stroke-width="1.5"><title>{esc(dt[5:])} {esc(txt[:80])}｜{lab} {_fmt(rr["r1"]) if rr else ""}</title></circle>')
    zero = Y(0)
    return (f'<svg class="spark" viewBox="0 0 {w} {h}" role="img" aria-label="株価の推移">'
            f'<line x1="0" x2="{w}" y1="{zero:.1f}" y2="{zero:.1f}" stroke="var(--line)" stroke-dasharray="2 3"/>'
            + (f'<polyline points="{bpts}" fill="none" stroke="var(--sub)" stroke-width="1" stroke-dasharray="3 3" opacity=".7"/>' if bpts else "")
            + f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2"/>' + "".join(dots)
            + f'<text x="4" y="{h-2}" class="ax">{esc(dates[0][5:])}</text><text x="{w-4}" y="{h-2}" class="ax" text-anchor="end">{esc(dates[-1][5:])}</text></svg>')


CSS = r'''
:root{--bg:#f6f7f9;--card:#fff;--ink:#1a1d23;--sub:#5b6270;--line:#e3e6eb;--up:#15803d;--dn:#dc2626;--chip:#f1f5f9}
@media (prefers-color-scheme:dark){:root{--bg:#121418;--card:#1b1e24;--ink:#e8eaee;--sub:#9aa1ad;--line:#2c313a;--up:#4ade80;--dn:#f87171;--chip:#242932}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,"Hiragino Sans","Noto Sans JP",sans-serif;line-height:1.6}
a{color:#2563eb}.wrap{max-width:1180px;margin:0 auto;padding:18px 16px 60px}.home{font-size:13px;margin-bottom:6px}
h1{font-size:22px;margin:0 0 2px}h2{font-size:17px;margin:28px 0 10px}.lead{color:var(--sub);font-size:13px;margin:0 0 14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px}
.mkt{display:grid;grid-template-columns:340px 1fr;gap:16px;align-items:center}@media(max-width:760px){.mkt{grid-template-columns:1fr}}
.kpis{display:flex;gap:14px;flex-wrap:wrap;font-size:13px}.kpis b{font-size:16px;display:block}
.up{color:var(--up)}.dn{color:var(--dn)}
.tw{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{border-bottom:1px solid var(--line);padding:7px 6px;text-align:left;vertical-align:top}th{font-size:11.5px;color:var(--sub);font-weight:600;white-space:nowrap}
td.n{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.lab{display:inline-block;font-size:11px;color:#fff;border-radius:9px;padding:0 8px;white-space:nowrap}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px}@media(max-width:400px){.grid{grid-template-columns:1fr}}
.sc h3{margin:0;font-size:15px;display:flex;justify-content:space-between;gap:8px;align-items:baseline}.sc .cd{font-size:11.5px;color:var(--sub);font-weight:400}
.px{font-size:12.5px;display:flex;gap:10px;flex-wrap:wrap;margin:2px 0 4px;font-variant-numeric:tabular-nums}
.spark{width:100%;height:auto;display:block;margin:4px 0}.spark .ax{font-size:9px;fill:var(--sub)}.nochart{font-size:12px;color:var(--sub);padding:18px 0;text-align:center}
.vw{font-size:12.5px;margin-top:6px}.vw div{margin:3px 0}.vw .k{font-size:11px;color:var(--sub);font-weight:600;margin-right:4px}
.sce{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:6px}.sce div{background:var(--chip);border-radius:8px;padding:6px 8px;font-size:12px}.sce .t{font-weight:700;font-size:11px}
.evl{list-style:none;margin:8px 0 0;padding:0;border-top:1px solid var(--line)}.evl li{font-size:12px;padding:5px 0;border-bottom:1px dashed var(--line);display:flex;gap:6px;align-items:flex-start}.evl .dt{color:var(--sub);white-space:nowrap}
.bar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}.search{border:1px solid var(--line);border-radius:8px;padding:6px 10px;font-size:13px;background:var(--card);color:var(--ink);min-width:200px}
.seg button{border:1px solid var(--line);background:var(--card);color:var(--ink);padding:5px 11px;font-size:12.5px;cursor:pointer;border-radius:8px}.seg button.on{background:#334155;color:#fff}
.watch{margin:6px 0 0;padding-left:18px;font-size:13px}.note{font-size:12px;color:var(--sub);margin-top:24px}
.legend{font-size:11.5px;color:var(--sub);display:flex;gap:10px;flex-wrap:wrap;margin-top:4px}.legend i{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:3px}
'''


def _today_rows(st, cos, date, codes=None):
    rows = []
    views = {cd: next((v for v in L if v["date"] == date), None) for cd, L in st.get("views", {}).items()}
    evs = _events(st, cos)
    for cd, L in evs.items():
        if cd == BENCH: continue
        e = next((x for x in L if x[0] == date), None)
        if not e: continue
        if codes is not None and cd not in codes: continue
        rr = _react(st, cd, date); v = views.get(cd)
        lab = _label(e[2], rr)
        rows.append((cd, st["names"].get(cd, {}).get("name", cd), e[1], rr, lab, v))
    rows.sort(key=lambda r: -abs((r[3] or {}).get("ex") if (r[3] or {}).get("ex") is not None else (r[3] or {}).get("r1") or 0))
    return rows


def _table(rows, link=True):
    if not rows: return '<p class="lead">きょうは株価と結びつけられる銘柄がありませんでした。</p>'
    tr = []
    for cd, name, txt, rr, (lab, lc), v in rows:
        nm = f'<a href="./stocks.html#s-{esc(cd)}">{esc(name)}</a>' if link else esc(name)
        tr.append(f'<tr><td>{nm}<div class="cd" style="font-size:11px;color:var(--sub)">{esc(cd)}</div></td><td>{esc(txt[:90])}</td>'
                  f'<td class="n {_cls(rr and rr["r1"])}">{_fmt(rr and rr["r1"])}</td><td class="n {_cls(rr and rr["ex"])}">{_fmt(rr and rr["ex"])}</td>'
                  f'<td><span class="lab" style="background:{lc}">{esc(lab)}</span></td><td>{esc((v or {}).get("outlook", ""))}</td></tr>')
    return ('<div class="tw"><table><thead><tr><th>銘柄</th><th>ニュース</th><th>当日</th><th>対日経</th><th>株価の受け止め</th><th>今後の見立て</th></tr></thead><tbody>'
            + "".join(tr) + '</tbody></table></div>')


def render_stocks(outdir):
    st = _load(outdir, "stocks.json", None)
    if not st: return 0
    cos = _load(outdir, "world_cos.json", {})
    evs = _events(st, cos)
    bser = _series(st, BENCH)
    today = bser[-1][0] if bser else datetime.date.today().isoformat()
    lastnews = max((L[-1][0] for L in evs.values() if L), default=today)
    # 地合い
    bi = len(bser) - 1
    kb = min(20, bi) if bser else 0
    k1, k5, k20 = (_ret(bser, bi, 1), _ret(bser, bi, 5), _ret(bser, bi, kb)) if bser else (None, None, None)
    mk = (st.get("market") or [{}])[-1]
    watch = "".join(f"<li>{esc(w)}</li>" for w in mk.get("watch", []))
    mkt = (f'<div class="card mkt"><div>{_chart(st, BENCH, [], 340, 110, 40)}<div class="legend">日経平均連動ETF（1321）の推移</div></div>'
           f'<div><div class="kpis"><div>前日比<b class="{_cls(k1)}">{_fmt(k1)}</b></div><div>5営業日<b class="{_cls(k5)}">{_fmt(k5)}</b></div><div>{kb}営業日<b class="{_cls(k20)}">{_fmt(k20)}</b></div></div>'
           f'<div class="vw"><div><span class="k">相場の見立て（{esc(mk.get("date", "")[5:])}）</span>{esc(mk.get("view", "—"))}</div></div>'
           + (f'<div class="vw"><span class="k">今後の注目イベント</span><ul class="watch">{watch}</ul></div>' if watch else "") + '</div></div>')
    # きょうの反応
    rows = _today_rows(st, cos, lastnews)
    # 反応ランキング（直近7日）
    t = datetime.date.fromisoformat(lastnews); big = []
    for cd, L in evs.items():
        if cd == BENCH: continue
        for dt, txt, tone in L:
            if (t - datetime.date.fromisoformat(dt)).days >= 7: continue
            rr = _react(st, cd, dt)
            if not rr: continue
            x = rr["ex"] if rr["ex"] is not None else rr["r1"]
            big.append((abs(x), dt, cd, txt, rr, _label(tone, rr)))
    big.sort(reverse=True)
    rk = "".join(f'<tr><td class="n">{esc(dt[5:])}</td><td><a href="#s-{esc(cd)}">{esc(st["names"].get(cd, {}).get("name", cd))}</a></td><td>{esc(txt[:80])}</td>'
                 f'<td class="n {_cls(rr["r1"])}">{_fmt(rr["r1"])}</td><td class="n {_cls(rr["ex"])}">{_fmt(rr["ex"])}</td><td class="n {_cls(rr["r5"])}">{_fmt(rr["r5"])}</td>'
                 f'<td><span class="lab" style="background:{lc}">{esc(lab)}</span></td></tr>' for _, dt, cd, txt, rr, (lab, lc) in big[:15])
    rank = ('<div class="card tw"><table><thead><tr><th>日付</th><th>銘柄</th><th>ニュース</th><th>当日</th><th>対日経</th><th>5日後</th><th>受け止め</th></tr></thead><tbody>' + rk + '</tbody></table></div>') if rk else '<p class="lead">データの蓄積待ちです。</p>'
    # 銘柄カード
    cards = []
    order = sorted([cd for cd in st["px"] if cd != BENCH and (cd in evs or cd in st.get("views", {}))],
                   key=lambda c: (evs.get(c, [("",)])[-1][0], c), reverse=True)
    for cd in order:
        nm = st["names"].get(cd, {}); ser = _series(st, cd); us = nm.get("mkt") == "us"
        if not ser: continue
        i = len(ser) - 1
        r1 = _ret(ser, i, 1) if not us else st["chg"].get(cd, {}).get(ser[-1][0])
        r5 = _ret(ser, i, 5); kn = min(20, i); r20 = _ret(ser, i, kn) if i >= 6 else None
        v = (st.get("views", {}).get(cd) or [None])[-1]
        L = evs.get(cd, [])
        evl = []
        for dt, txt, tone in reversed(L[-8:]):
            rr = _react(st, cd, dt); lab, lc = _label(tone, rr)
            evl.append(f'<li><span class="dt">{esc(dt[5:])}</span><span style="flex:1">{esc(txt[:110])}</span><span class="n {_cls(rr and (rr["ex"] if rr["ex"] is not None else rr["r1"]))}" style="white-space:nowrap">{_fmt(rr and (rr["ex"] if rr["ex"] is not None else rr["r1"]))}</span><span class="lab" style="background:{lc}">{esc(lab)}</span></li>')
        vw = ""
        if v:
            vw = (f'<div class="vw"><div><span class="k">動かしている要因</span>{esc(v.get("drivers", ""))}</div><div><span class="k">今後の見立て（{esc(v["date"][5:])}）</span>{esc(v.get("outlook", ""))}</div></div>'
                  f'<div class="sce"><div><div class="t up">▲ 上振れシナリオ</div>{esc(v.get("up", ""))}</div><div><div class="t dn">▼ 下振れシナリオ</div>{esc(v.get("down", ""))}</div></div>'
                  + (f'<div class="vw"><span class="k">次の注目</span>{esc(v.get("watch", ""))}</div>' if v.get("watch") else ""))
        unit = "$" if us else "円"
        cards.append(f'<div class="card sc" id="s-{esc(cd)}" data-q="{esc(nm.get("name", ""))} {esc(cd)} {esc(nm.get("ind", ""))}" data-m="{"us" if us else "jp"}">'
                     f'<h3><span>{esc(nm.get("name", cd))} <span class="cd">{esc(cd)}・{esc(nm.get("ind", ""))}</span></span></h3>'
                     f'<div class="px"><span>{ser[-1][1]:,.1f}{unit}（{esc(ser[-1][0][5:])}）</span><span class="{_cls(r1)}">前日比 {_fmt(r1)}</span><span class="{_cls(r5)}">5日 {_fmt(r5)}</span><span class="{_cls(r20)}">{kn}日 {_fmt(r20)}</span></div>'
                     f'{_chart(st, cd, L)}{vw}<ul class="evl">{"".join(evl)}</ul></div>')
    body = f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>株価×ニュース</title><style>{CSS}</style></head><body><div class="wrap">
<div class="home"><a href="./index.html">← ダッシュボードへ戻る</a></div>
<h1>📈 株価×ニュース</h1>
<p class="lead">ダイジェストに登場した企業について、ニュースが出た日の株価の反応（当日の騰落率と、日経平均連動ETFに対する超過分）と、その後の値動きを追います。今後の見立ては上振れ・下振れのシナリオとトリガーで示します。株価は日経会社情報の終値（最新：{esc(today)}）。</p>
<h2>相場の地合い</h2>{mkt}
<h2>きょうのニュースと株価の反応（{esc(lastnews)}付）</h2><div class="card">{_table(rows)}</div>
<h2>反応が大きかったニュース（直近7日）</h2>{rank}
<h2>銘柄ごとの値動きとニュース</h2>
<div class="bar"><input class="search" id="q" placeholder="企業名・コード・業種で絞り込み"><div class="seg" id="mk"><button data-m="all" class="on">すべて</button><button data-m="jp">国内</button><button data-m="us">海外</button></div></div>
<div class="legend"><span>グラフ：実線＝株価（期間の初日を0%）、点線＝日経平均連動ETF。点＝ニュースが出た日（色は株価の受け止め）</span><span><i style="background:#16a34a"></i>好感・買われる</span><span><i style="background:#dc2626"></i>失望・売られる</span><span><i style="background:#d97706"></i>材料出尽くし</span><span><i style="background:#7c3aed"></i>逆行高</span><span><i style="background:#94a3b8"></i>反応薄（±1%未満）</span></div>
<div class="grid" id="cards" style="margin-top:10px">{"".join(cards)}</div>
<p class="note">「当日」はニュースが紙面に載った日（またはその後の最初の取引日）の終値ベースの騰落率、「対日経」はそこから日経平均連動ETF（1321）の騰落率を引いた超過分。ニュース以外の要因（地合い・需給）も含むため、因果関係を断定するものではありません。投資判断の助言ではありません。</p>
</div><script>
const q=document.getElementById('q'),cs=[...document.querySelectorAll('#cards .sc')];let m='all';
function f(){{const t=q.value.trim();cs.forEach(c=>{{c.style.display=((!t||c.dataset.q.includes(t))&&(m==='all'||c.dataset.m===m))?'':'none'}})}}
q.addEventListener('input',f);document.querySelectorAll('#mk button').forEach(b=>b.onclick=()=>{{m=b.dataset.m;document.querySelectorAll('#mk button').forEach(x=>x.classList.toggle('on',x===b));f()}});
</script></body></html>'''
    with open(_p(outdir, "stocks.html"), "w", encoding="utf-8") as f: f.write(body)
    return len(cards)


def digest_block(d, outdir):
    st = _load(outdir, "stocks.json", None)
    if not st: return ""
    cos = _load(outdir, "world_cos.json", {})
    rows = _today_rows(st, cos, d["date_iso"])
    if not rows: return ""
    mk = (d.get("stocks") or {}).get("market") or {}
    head = f'<p class="lead">{esc(mk.get("view", ""))}</p>' if mk.get("view") else ""
    return (f'<section id="stock"><h2><span class="num">📈</span>株価の反応（ニュース×株価）</h2>{head}'
            f'<p class="lead">きょう登場した企業の株価の受け止め。「対日経」は日経平均連動ETFに対する超過分。詳しい値動きとシナリオは<a href="./stocks.html">株価×ニュース</a>へ。</p>'
            f'<style>.sttab table{{border-collapse:collapse;width:100%;font-size:13px}}.sttab th,.sttab td{{border-bottom:1px solid #e5e7eb;padding:6px;text-align:left;vertical-align:top}}.sttab td.n{{text-align:right;white-space:nowrap}}.sttab .up{{color:#15803d}}.sttab .dn{{color:#dc2626}}.sttab .lab{{display:inline-block;font-size:11px;color:#fff;border-radius:9px;padding:0 8px;white-space:nowrap}}</style>'
            f'<div class="sttab">{_table(rows)}</div></section>')


def index_teaser(outdir):
    st = _load(outdir, "stocks.json", None)
    if not st: return ""
    cos = _load(outdir, "world_cos.json", {})
    evs = _events(st, cos)
    lastnews = max((L[-1][0] for L in evs.values() if L), default="")
    rows = _today_rows(st, cos, lastnews)[:5]
    items = "".join(f'<li><a href="./stocks.html#s-{esc(cd)}">{esc(name)}</a> <span class="{_cls(rr and (rr["ex"] if rr["ex"] is not None else rr["r1"]))}">{_fmt(rr and (rr["ex"] if rr["ex"] is not None else rr["r1"]))}</span> <span class="lab" style="background:{lc}">{esc(lab)}</span> <span style="color:#64748b">{esc(txt[:40])}</span></li>' for cd, name, txt, rr, (lab, lc), v in rows)
    return (f'<section id="stocks"><style>#stocks ul{{list-style:none;padding:0;margin:0}}#stocks li{{padding:6px 0;border-bottom:1px solid #e5e7eb;font-size:13.5px}}#stocks .up{{color:#15803d;font-weight:700}}#stocks .dn{{color:#dc2626;font-weight:700}}#stocks .lab{{font-size:11px;color:#fff;border-radius:9px;padding:0 7px}}</style>'
            f'<h2><span class="num">📈</span>株価×ニュース</h2><p class="lead">きょうのニュースに株価はどう反応したか（対日経の超過分が大きい順）。値動きの推移と今後のシナリオは専用ページで。</p>'
            f'<ul>{items}</ul><a class="wt-cta" href="./stocks.html" style="display:inline-block;margin-top:10px;font-weight:700">→ 株価×ニュースを見る</a></section>')
