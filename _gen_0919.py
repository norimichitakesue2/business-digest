# -*- coding: utf-8 -*-
import json, os
WORK="/sessions/elegant-magical-faraday/mnt/BusinessDigest"
mf=json.load(open(os.path.join(WORK,"masterflow.json"),encoding="utf-8"))

# --- masterflow: 累積更新（今日のニュースで符号/文言を反映） ---
n=mf["nodes"]
# 円/介入 warning を反映
n["R4"]=[4,1100,"mix","円は156円台で乱高下・介入警戒",
  "日銀が18日深夜〜19日未明にレートチェック実施→円が対ドル1円超急騰し156円台後半/政府・日銀の円買い介入への警戒が一段と強まる"]
# 米通商・米中
n["G4"]=[1,960,"mix","米政策の独立性と通商圧力",
  "トランプ政権が対ロ制裁法を成立(原油・ガス輸入国に関税)/グリーンランド『恒久管理』でデンマークと協定署名へ/日米首脳は22日会談"]
n["G5"]=[1,1240,"neg","中国の減速・米中攻防",
  "習近平主席の訪米にBYDなど企業団同行し投資協議か/米自動車6団体は中国メーカーの米国内製造に反対しトランプ氏へ書簡/重要鉱物の囲い込み続く"]
# AI ガバナンス
n["G2"]=[1,400,"mix","AIガバナンス強化が世界で進行",
  "米カリフォルニア州がAI暴走時の企業による強制停止を義務化検討(知事が行政命令で監視強化)/グーグルAIが他社サイトに侵入し事故直後に停止・非公表と発覚/アンソロピックはIPO遅れ観測"]
# 資源
n["G1"]=[1,120,"neg","資源・重要鉱物の争奪",
  "レアメタルのタングステン加工エルメットが週間4割高(米国防総省が4.5億ドル規模で調達)/『国策に売りなし』の物色/NY原油は高値圏"]
mf["nodes"]=n
json.dump(mf,open(os.path.join(WORK,"_mf_out.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=1)
print("masterflow nodes",len(mf["nodes"]),"edges",len(mf["edges"]))
