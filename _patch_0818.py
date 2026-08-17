# -*- coding: utf-8 -*-
import json,os
W=os.path.dirname(os.path.abspath(__file__))
d=json.load(open(os.path.join(W,"day_data.json"),encoding="utf-8"))

# 1) enrich top market item with Chrome-sourced Nikkei 8/18 article
for n in d["news"]:
    if n["head"].startswith("日経平均5日続伸"):
        n["head"]="4-6月最高益530社 AI特需で半導体・材料・建設『黒子』に波及"
        n["ind"]="マーケット・為替"
        n["url"]="https://www.nikkei.com/article/DGXZQOUB128CK0S6A810C2000000/"
        n["bg"]="日経新聞が約1900社の4-6月決算を集計。生成AIの急拡大で半導体・DC関連が牽引し、恩恵が幅広い業種に波及した。日経平均は8/17まで5日続伸し6万9220円と1カ月半ぶり高値。"
        n["summ"]="上場企業の3社に1社(約530社・28%)が4-6月に純利益で最高益。コロナ後で最高の比率。アドバンテストは純益+94%、フジクラは2.6倍、TDKは+90%、旭化成は5年ぶり最高益。半導体材料や建設『サブコン』にも恩恵が広がった。"
        n["points"]=["約530社(28%)が最高益、コロナ後で最高比率","アドバンテスト+94%・フジクラ2.6倍・TDK+90%","日産化学・扶桑化学など半導体材料が好調","関電工・エクシオGなどDC建設サブコンも最高益"]
        n["forecast"]="東証プライムの27年3月期純利益は前期比+14%と堅調見込み。原材料高を価格転嫁できる限り好業績が続くとの見方。AI・DC関連の裾野拡大が相場の支え。"
        n["study"]=["【決算】最高益比率とAI波及","【部材】半導体材料の寡占と単価","【建設】DCサブコンの受注","【相場】業績相場の持続力"]
        n["pos"]="AI特需で最高益の裾野拡大"
        n["neg"]="価格転嫁の限界/高値警戒"

# 2) enrich 精密・電子部品 with real names
for n in d["news"]:
    if n["ind"]=="精密・電子部品":
        n["head"]="アドバンテスト+94%・フジクラ2.6倍 AI試験装置・光ファイバが牽引"
        n["url"]="https://www.nikkei.com/article/DGXZQOUB128CK0S6A810C2000000/"
        n["summ"]="AI推論向けの半導体試験装置が伸びアドバンテストは純益+94%。フジクラは海外ハイパースケーラーのDC投資を追い風に光ファイバ関連が好調で純益2.6倍。TDKもAI DC向けMLCC・電解コンデンサで+90%。"
        n["points"]=["アドバンテスト 純益+94%(AI試験装置)","フジクラ 純益2.6倍(光ファイバ/DC投資)","TDK +90%(MLCC・コンデンサ・構造改革)","AI推論需要が電子部品に波及"]

# 3) enrich 建設・重電 with サブコン names
for n in d["news"]:
    if n["ind"]=="建設・重電":
        n["head"]="DC建設ラッシュでサブコン最高益 関電工・エクシオG営業益15倍"
        n["url"]="https://www.nikkei.com/article/DGXZQOUB128CK0S6A810C2000000/"
        n["summ"]="データセンター増設で通信・電機の専門工事会社(サブコン)に最高益が相次ぐ。関電工は屋内線・環境設備工事が好調でDC受注が急増。エクシオグループはDC工事を含む社会インフラ事業の営業利益が15倍に。"
        n["points"]=["DC増設でサブコンが最高益","関電工 DC受注・完成工事が大幅増","エクシオG 社会インフラ営業益15倍","重電・電線に構造需要が波及"]

# 4) add Chrome-sourced companies
add=[
 ["アドバンテスト","6857","半導体","約12兆円","AI推論向けの半導体試験装置が伸び4-6月純益+94%。AI・DC需要の裾野拡大が追い風。","AI試験装置需要","市況変動/高PER"],
 ["フジクラ","5803","電線・電子部品","約4兆円","海外ハイパースケーラーのDC投資を追い風に光ファイバ関連が好調、4-6月純益2.6倍。","DC投資/光ファイバ需要","需要一巡リスク"],
 ["TDK","6762","電子部品","約6兆円","AI DC向けMLCC・アルミ電解コンデンサ販売増と構造改革効果で4-6月純益+90%。","AI DC部材/構造改革","為替/在庫調整"],
 ["関電工","1942","建設(サブコン)","約4000億円","DC増設で屋内線・環境設備工事が好調、受注高・完成工事高が前年を大きく上回り最高益。","DC建設サブコン需要","人手・資材コスト"],
]
names={c[0] for c in d["companies"]}
for c in add:
    if c[0] not in names: d["companies"].append(c)

json.dump(d,open(os.path.join(W,"day_data.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=1)
print("patched. news:",len(d["news"]),"companies:",len(d["companies"]))
