import json
st=json.load(open('streams.json')); B={s['id']:s for s in st['streams']}
D='2026-11-12'
r=B['rate']; r['name']='物価・金利・財政の正常化'
r['one']='日本は「金利ある世界」へ戻る途中。物価高が家計の節約を招き、国債費の増加で財政の信認も問われる。為替・住宅ローン・預金金利・消費に波及する。'
r['mech']=['物価高・賃上げ・日銀の利上げ','長期金利・為替の変動','国債費・家計の負担増','消費・住宅・預金への波及']
r['qs']=['cb','jgb','fx','tax','banks','household','foodinf']; r['kws']=['金利','日銀','円','国債','財政','税','物価','値上げ','消費支出']
r.setdefault('phase_hist',[]).append({'date':D,'phase':r.get('phase',1),'why':'名称を「物価・金利・財政の正常化」に変更し、物価高・家計消費も対象に含めた'})
b=B['bloc']; b['one']='関税・輸出規制・経済安保で世界がブロックに分かれつつある。資源・技術の囲い込みとサプライチェーンの組み替えが進む。'
b['mech']=['米中の技術・通商対立','関税・輸出規制・経済安保','サプライチェーンの組み替え','国産化・調達先分散の需要']
b['qs']=['trade','minerals','sovai']; b['kws']=['関税','経済安保','輸出規制','レアアース','APEC']
d=B['demo']; d['qs']=['labor','logi']
new=[
{"id":"cyber","name":"サイバー攻撃とデジタルの信頼","color":"#db2777","flags":["jp","us","cn","kp"],
 "one":"委託先やID基盤を狙う大量流出が日常になった。企業は防御・保険・「持たない」選択を迫られ、国は通信監視まで踏み込む法改正を議論している。",
 "mech":["AIで高度化する攻撃・委託先経由の侵入","大量流出・業務停止","防御投資・保険・補償コスト","法制強化と通信の秘密の調整"],
 "hist":"2017年のWannaCryと、2014年のベネッセ個人情報流出","qs":["cyber","sovai"],"kws":["サイバー","不正アクセス","流出","漏洩","ランサム"],"phase":2,
 "why":"新設：国内の攻撃公表が月233件と最多、ニトリ3762万件など大量流出が連鎖（従来は経済安保・安保に分散していた記事を独立）"},
{"id":"gov","name":"資本効率の要求と企業再編","color":"#a16207","flags":["jp","us","gb","se"],
 "one":"東証の資本効率改善の要請と割安な株価が、アクティビスト・PEファンド・同業による買収を呼び込んでいる。非公開化・事業売却・系列を超えた再編が相次ぐ。",
 "mech":["東証のPBR改善要請・割安株","アクティビスト・PE・同業のTOB","非公開化・事業売却・持ち合い解消","経営の説明責任と少数株主保護"],
 "hist":"2000年代半ばの村上ファンド・スティール・パートナーズの攻勢と、2006年の王子製紙による北越製紙TOB","qs":["govern","market","regional"],"kws":["TOB","買収","アクティビスト","株主提案","非公開化","再編"],"phase":1,
 "why":"新設：宝HD・北陸電気・カカクコム・メディパル等の攻防が続き、どの流れにも属さない記事が多かった"},
]
for n in new:
    e={k:v for k,v in n.items() if k not in('phase','why')}
    e.update({"phase":n['phase'],"phase_hist":[{"date":D,"phase":n['phase'],"why":n['why']}],"ind":[],"branch":"","born":D})
    if n['id'] not in B: st['streams'].append(e)
st['streams'][[s['id'] for s in st['streams']].index('cyber')]['ind']=[["国内のサイバー攻撃の公表（10月）","233件（月間最多）"],["ニトリの流出可能性","最大3762万件"],["シェアフルの流出可能性","約750万件"]]
st['streams'][[s['id'] for s in st['streams']].index('cyber')]['branch']='能動的サイバー防御法の改正案で国内通信の監視・遮断をどこまで認めるか'
st['streams'][[s['id'] for s in st['streams']].index('gov')]['ind']=[["ベインの北陸電気TOB","328億円"],["宝HDの臨時総会","12月16日（バリューアクトの6議案）"],["カカクコム","EQTが1株3000円でTOB、LINEヤフーが対抗"]]
st['streams'][[s['id'] for s in st['streams']].index('gov')]['branch']='12月の宝HD・メディパルの臨時総会の結果と、カカクコム争奪の決着'
B['sec']['ind']=[x for x in B['sec'].get('ind',[]) if '流出' not in x[0]]
L=st.setdefault('links',[])
for l in [["cyber","bloc","国家の関与→経済安保"],["rate","gov","金利上昇・PBR要請→資本効率の圧力"],["gov","ai","再編マネー→半導体素材・AIへの集中"]]:
    if l not in L: L.append(l)
json.dump(st,open('streams.json','w'),ensure_ascii=False,indent=1)

w=json.load(open('world_news.json'))
fix={}
for i in [29,30,31,53,54,55,56,82,83,110,111,150,151,152,175,176,196,207,229,230,231,244,245]: fix[i]='cyber'
for i in [21,37,48,87,88,89,102,127,135,136,195,201,208,214,237,240,255,256,262]: fix[i]='gov'
for i in [2,3,23,46,51,70,72,198,227,253,263]: fix[i]='rate'
for i in [27,32,33,36,49,50,90,105,133,138,159,174,192,224,225]: fix[i]=None
for i in [74,76,142,157,189,218]: fix[i]='mideast'
chg=[]
for i,s in fix.items():
    if w[i]['s']!=s: chg.append((i,w[i]['date'],w[i]['s'],s,w[i]['head'][:30])); w[i]['s']=s; w[i]['fixed']=D
json.dump(w,open('world_news.json','w'),ensure_ascii=False,indent=1)
json.dump(chg,open('_reclass_1112.json','w'),ensure_ascii=False,indent=1)
# keep today's day_data in sync
dd=json.load(open('day_data.json'))
for n in dd['news']:
    for x in w:
        if x['date']==dd['date_iso'] and x['head']==n['head']: n['world']['s']=x['s']
json.dump(dd,open('day_data.json','w'),ensure_ascii=False,indent=1)
from collections import Counter
print(len(chg), Counter(x['s'] for x in w))
