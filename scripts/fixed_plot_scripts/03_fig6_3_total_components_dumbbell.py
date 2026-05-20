
import pandas as pd, numpy as np, matplotlib.pyplot as plt
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Plots' / 'thesis_plot_scripts_projectpaths'; OUT.mkdir(parents=True, exist_ok=True)
PAIR_LABELS={'maps':'Yandex Maps vs Google Maps','taxi':'Yandex Go Taxi vs Bolt','rail1':'RZD vs DB Navigator','rail2':'Yandex Trains vs Mobiliteit.lu',
'ecom1':'Ozon vs Amazon Shopping','ecom2':'Wildberries vs Zalando','ecom3':'Yandex Market vs bol','ecom4':'Avito vs Vinted','bank1':'Sberbank vs BGL',
'bank2':'Tinkoff vs ING Luxembourg','bank3':'Alfa Bank vs Revolut','bank4':'VTB vs BILnet','health':'EMIAS.INFO vs Doctena','social1':'VK vs Facebook',
'social2':'OK vs X','msg1':'MAX vs WhatsApp','msg2':'Yandex Telemost vs Telegram','gov1':'Gosuslugi vs MyGuichet.lu','gov2':'Nalogi FL vs impots.gouv','gov3':'Gosuslugi Biometria vs itsme'}
pairs=pd.read_csv(ROOT/'results/local/extracted_local_manifest_features and lists.csv')
local=pd.read_csv(ROOT/'results/local/local_from_manifest.csv')
df=pairs.merge(local,on='sha256',how='inner')
df['total_components']=df['activities_local'].fillna(0)+df['services_local'].fillna(0)+df['receivers_local'].fillna(0)+df['providers_local'].fillna(0)
wide=df[['pair_id','group','total_components']].drop_duplicates().pivot_table(index='pair_id',columns='group',values='total_components',aggfunc='first').reset_index().dropna(subset=['ru','eu'])
wide['abs_diff']=(wide['ru']-wide['eu']).abs()
wide=wide.sort_values(['abs_diff','ru','eu'],ascending=[True,False,False]).reset_index(drop=True)
y=np.arange(len(wide))
ru_color,eu_color='#134686','#ED3F27'
fig,ax=plt.subplots(figsize=(10.8,8.0))
for i,row in enumerate(wide.itertuples(index=False)):
    ax.plot([row.ru,row.eu],[i,i],color='#C9D1D9',linewidth=2,zorder=1)
ax.scatter(wide['ru'],y,s=70,marker='o',color=ru_color,label='RU',zorder=3)
ax.scatter(wide['eu'],y,s=70,marker='D',color=eu_color,label='EU',zorder=3)
ax.set_xlim(0, 1300)
ax.set_xticks([0, 300, 600, 900, 1200])

ax.set_yticks(y); ax.set_yticklabels([PAIR_LABELS.get(p,p) for p in wide['pair_id']],fontsize=10)
ax.set_xlabel('Total components count (log scale)',fontsize=11)
ax.set_title('Total Android components by matched RU-EU app pair',fontsize=14,pad=12)
ax.grid(axis='x', linestyle=':', linewidth=0.8, alpha=0.18)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
ax.legend(frameon=False, loc='lower right')
fig.tight_layout(); out=OUT/'fig6_3_total_components_dumbbell.png'; fig.savefig(out,dpi=300,bbox_inches='tight'); print(out)
