# -*- coding: utf-8 -*-
import json

sectors_delta = {
 "new_sectors": [
  {"key":"sovai","name":"データ主権・国産サイバー防御","color":"#0d9488",
   "lead":"生成AIの普及で機密データの国外流出リスクが顕在化。AI処理を国内で完結させる『データ主権』の需要が、国産クラウド・国産LLM・国内DCへの投資を押し上げる。",
   "flow":{
     "nodes":{
       "u1":[1,40,"pos","国産半導体・GPU調達","国内で確保する推論・学習用チップ"],
       "u2":[1,124,"pos","国内データセンター立地","機密データを国内に留める基盤"],
       "u3":[1,208,"mix","国産LLM・基盤モデル","自国運用の大規模言語モデル"],
       "m1":[2,40,"pos","AI脆弱性診断エンジン","ソースコードを国外に出さず欠陥検出"],
       "m2":[2,124,"pos","秘匿計算・データ最小化","データを守りつつAI解析"],
       "m3":[2,208,"neg","セキュリティ人材","慢性的な人材不足がボトルネック"],
       "d1":[3,40,"pos","国内完結サイバー防御サービス","NTT・SBが展開拡大"],
       "d2":[3,124,"pos","政府・重要インフラ調達","データ主権を前提の調達基準"],
       "d3":[3,208,"mix","金融・製造の機密データ運用","規制業種での採用"],
       "r1":[4,40,"pos","データ主権需要の拡大","ソブリンAI潮流で市場拡大"],
       "r2":[4,124,"pos","国産クラウド市場","国内基盤への投資増"]
     },
     "edges":[
       ["u1","m1","pos","国産チップ"],
       ["u2","d1","pos","国内基盤"],
       ["u3","m1","pos","国産モデル"],
       ["m1","d1","pos","診断提供"],
       ["m2","d3","pos","秘匿解析"],
       ["m3","d1","neg","人材不足"],
       ["d1","r1","pos","サービス供給"],
       ["d2","r1","pos","公需拡大"],
       ["d3","r2","pos","国産採用"],
       ["u2","r2","pos","DC投資"]
     ]
   },
   "meta":{
     "u1":{"companies":[["ラピダス","国産先端半導体"],["ソシオネクスト","設計"]],"aliases":["国産半導体","GPU","推論チップ"],"desc":"国内で確保するAI用の学習・推論チップ。海外依存を下げデータ主権の土台となる。","why":"国産調達は主権確保の起点でプラス"},
     "u2":{"companies":[["さくらインターネット","国産クラウド・DC"],["NTT","データセンター"]],"aliases":["データセンター","国内DC","立地"],"desc":"機密データを国内に留めて処理するための国内データセンター基盤。","why":"国内立地は主権需要の受け皿でプラス"},
     "u3":{"companies":[["NTT","tsuzumi"],["NEC","cotomi"]],"aliases":["国産LLM","基盤モデル","LLM"],"desc":"自国のインフラとデータで運用する大規模言語モデル。性能と主権の両立が課題。","why":"性能面の制約もあり評価は混在"},
     "m1":{"companies":[["NTT","脆弱性診断"],["ソフトバンク","AI防御"]],"aliases":["脆弱性診断","サイバー防御","ソースコード"],"desc":"ソースコードを国外に出さずにAIでシステムの欠陥を洗い出す診断エンジン。","why":"国内完結の中核機能でプラス"},
     "m2":{"companies":[["各セキュリティ企業","秘匿計算"]],"aliases":["秘匿計算","データ最小化","プライバシー"],"desc":"データを保護したままAI解析する技術。機密性の高い業種で需要。","why":"主権と活用を両立させプラス"},
     "m3":{"companies":[["各社","人材採用"]],"aliases":["セキュリティ人材","人材不足"],"desc":"サイバー防御を担う専門人材。慢性的な不足が普及の足かせ。","why":"人材不足がボトルネックでマイナス"},
     "d1":{"companies":[["NTT","国内完結防御"],["ソフトバンク","AI防御"]],"aliases":["国内完結","サイバー防御サービス","データ主権"],"desc":"顧客データを国外に送らずに脆弱性診断を行う国内完結型の防御サービス。","why":"新規需要を取り込みプラス"},
     "d2":{"companies":[["政府","重要インフラ"]],"aliases":["政府調達","重要インフラ","公需"],"desc":"データ主権を前提とした政府・重要インフラのセキュリティ調達。","why":"公需拡大でプラス"},
     "d3":{"companies":[["金融機関","製造業"]],"aliases":["金融","製造","機密データ"],"desc":"規制業種での機密データのAI運用。採用は規制と性能次第。","why":"導入は進むが制約もあり混在"},
     "r1":{"companies":[["国内IT各社","ソブリンAI"]],"aliases":["データ主権","ソブリンAI","市場拡大"],"desc":"自国内でAIを運用するソブリンAIの潮流で拡大する需要。","why":"構造的な需要拡大でプラス"},
     "r2":{"companies":[["さくらインターネット","国産クラウド"]],"aliases":["国産クラウド","クラウド市場"],"desc":"国内基盤への投資増で拡大する国産クラウド市場。","why":"投資拡大でプラス"}
   }
  }
 ],
 "add_nodes":{
   "humanoid":{
     "spatial1":[1,780,"pos","空間知能・ワールドモデル(World Labs/AMD)","AMDが82億ドルで買収。3次元空間理解でロボ・自動運転の基盤に"]
   }
 },
 "add_edges":{
   "humanoid":[
     ["spatial1","d1","pos","空間認識で実装"]
   ]
 },
 "add_meta":{
   "humanoid":{
     "spatial1":{"companies":[["AMD","World Labs買収"],["フェイフェイ・リー","創業者"]],
       "aliases":["空間知能","ワールドモデル","World Labs","フィジカルAI","AMD"],
       "desc":"現実世界の3次元空間を理解・生成するAI。ロボットや自動運転が現実で動くための基盤技術。","why":"ヒューマノイド実装を加速させプラス"}
   }
 }
}
json.dump(sectors_delta, open("_sd.json","w",encoding="utf-8"), ensure_ascii=False)
print("sectors_delta ok: new_sectors",len(sectors_delta["new_sectors"]),
      "add_nodes", sum(len(v) for v in sectors_delta["add_nodes"].values()),
      "add_edges", sum(len(v) for v in sectors_delta["add_edges"].values()))

# ---- assemble final day_data.json ----
p1 = json.load(open("_p1.json",encoding="utf-8"))
news = json.load(open("_news.json",encoding="utf-8"))
p2 = json.load(open("_p2.json",encoding="utf-8"))
doc = {
 "date_label": p1["date_label"],
 "date_iso": p1["date_iso"],
 "flow": p1["flow"],
 "masterflow": p1["masterflow"],
 "trends": p1["trends"],
 "news": news,
 "companies": p2["companies"],
 "preds": p2["preds"],
 "deeps": p2["deeps"],
 "sectors_delta": sectors_delta
}
json.dump(doc, open("day_data.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
print("day_data.json written")
# quick sanity: sent/kind value domains
sent_ok={"pos","neg","mix","drv"}; kind_ok={"pos","neg","mix","ease"}
def chk(flow,name):
    for nid,v in flow["nodes"].items():
        assert v[2] in sent_ok, f"{name} node {nid} bad sent {v[2]}"
    for e in flow["edges"]:
        assert e[2] in kind_ok, f"{name} edge {e} bad kind"
chk(doc["flow"],"flow"); chk(doc["masterflow"],"masterflow")
for s in sectors_delta["new_sectors"]:
    chk(s["flow"], "sector "+s["key"])
for k,nodes in sectors_delta["add_nodes"].items():
    for nid,v in nodes.items(): assert v[2] in sent_ok
for k,edges in sectors_delta["add_edges"].items():
    for e in edges: assert e[2] in kind_ok
print("sent/kind domains OK")
