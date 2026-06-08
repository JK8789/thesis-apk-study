
import pandas as pd, numpy as np, matplotlib.pyplot as plt
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Plots' / 'thesis_plot_scripts_projectpaths'; OUT.mkdir(parents=True, exist_ok=True)
PAIR_LABELS={'maps':'Yandex Maps vs Google Maps','taxi':'Yandex Go Taxi vs Bolt','rail1':'RZD vs DB Navigator','rail2':'Yandex Trains vs Mobiliteit.lu',
'ecom1':'Ozon vs Amazon Shopping','ecom2':'Wildberries vs Zalando','ecom3':'Yandex Market vs bol','ecom4':'Avito vs Vinted','bank1':'Sberbank vs BGL',
'bank2':'Tinkoff vs ING Luxembourg','bank3':'Alfa Bank vs Revolut','bank4':'VTB vs BILnet','health':'EMIAS.INFO vs Doctena','social1':'VK vs Facebook',
'social2':'OK vs X','msg1':'MAX vs WhatsApp','msg2':'Yandex Telemost vs Telegram','gov1':'Gosuslugi vs MyGuichet.lu','gov2':'Nalogi FL vs impots.gouv','gov3':'Gosuslugi Biometria vs itsme'}
pairs = pd.read_csv(ROOT/'results/libs_longest/pairs_libs_diff.csv')
pair_col='pair_id'
ru_cand=[c for c in pairs.columns if c.lower() in ['ru_count','ru_hits','ru_total','count_ru','ru']]
eu_cand=[c for c in pairs.columns if c.lower() in ['eu_count','eu_hits','eu_total','count_eu','eu']]
if ru_cand and eu_cand:
    wide=pairs[[pair_col,ru_cand[0],eu_cand[0]]].rename(columns={ru_cand[0]:'ru',eu_cand[0]:'eu'})
else:
    df=pd.read_csv(ROOT/'results/libs_longest/libs_per_app_long.csv')
    pair_col=[c for c in df.columns if c.lower()=='pair_id'][0]
    group_col=[c for c in df.columns if c.lower() in ['group','region']][0]
    prefix_col=[c for c in df.columns if 'prefix' in c.lower()][0]
    agg=df.groupby([pair_col,group_col])[prefix_col].nunique().reset_index(name='hits')
    wide=agg.pivot_table(index=pair_col,columns=group_col,values='hits',aggfunc='first').reset_index()
wide=wide.dropna(subset=['ru','eu']).copy()
wide['total']=wide['ru']+wide['eu']
wide=wide.sort_values(['total','ru'], ascending=[False,False]).reset_index(drop=True)
y=np.arange(len(wide))
ru_color,eu_color='#3852B4','#FF8C00'
fig,ax=plt.subplots(figsize=(10.8,8.0))
for i,row in enumerate(wide.itertuples(index=False)):
    ax.plot([row.ru,row.eu],[i,i],color='#D7D1CC',linewidth=2,zorder=1)
ax.scatter(wide['ru'],y,s=65,marker='o',color=ru_color,label='RU',zorder=3)
ax.scatter(wide['eu'],y,s=65,marker='D',color=eu_color,label='EU',zorder=3)
ax.set_yticks(y); ax.set_yticklabels([PAIR_LABELS.get(p,p) for p in wide[pair_col]],fontsize=15)
ax.tick_params(axis='x', labelsize=15)
ax.set_xlabel('Detected Maven SDK hits',fontsize=15)
ax.set_title('Total detected Maven SDK hits by matched pair',fontsize=14,pad=12)
mx=int(max(wide['ru'].max(),wide['eu'].max())+2)
ax.set_xticks(np.arange(0,mx+1,2))
ax.grid(axis='x', linestyle=':', linewidth=0.8, alpha=0.18)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
ax.legend(frameon=False, loc='upper right', fontsize=15)
fig.tight_layout(); out=OUT/'fig6_5_total_sdk_hits_dumbbell_without_num.png'; fig.savefig(out,dpi=300,bbox_inches='tight'); print(out)
