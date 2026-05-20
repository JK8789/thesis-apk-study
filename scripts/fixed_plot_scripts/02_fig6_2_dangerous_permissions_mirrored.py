
import pandas as pd, numpy as np, matplotlib.pyplot as plt
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Plots' / 'thesis_plot_scripts_projectpaths'; OUT.mkdir(parents=True, exist_ok=True)
PAIR_LABELS = {
    'maps':'Yandex Maps vs Google Maps','taxi':'Yandex Go Taxi vs Bolt','rail1':'RZD vs DB Navigator','rail2':'Yandex Trains vs Mobiliteit.lu',
    'ecom1':'Ozon vs Amazon Shopping','ecom2':'Wildberries vs Zalando','ecom3':'Yandex Market vs bol','ecom4':'Avito vs Vinted',
    'bank1':'Sberbank vs BGL','bank2':'Tinkoff vs ING Luxembourg','bank3':'Alfa Bank vs Revolut','bank4':'VTB vs BILnet',
    'health':'EMIAS.INFO vs Doctena','social1':'VK vs Facebook','social2':'OK vs X','msg1':'MAX vs WhatsApp','msg2':'Yandex Telemost vs Telegram',
    'gov1':'Gosuslugi vs MyGuichet.lu','gov2':'Nalogi FL vs impots.gouv','gov3':'Gosuslugi Biometria vs itsme',
}
pairs = pd.read_csv(ROOT/'results/local/extracted_local_manifest_features and lists.csv')
cand=[c for c in pairs.columns if c.lower() in ['dangerous_permissions_count','dangerous_perm_count','dangerous_count']]
if not cand:
    raise ValueError(f'Need dangerous permissions column in extracted file; available={pairs.columns.tolist()}')
df=pairs[['pair_id','group',cand[0]]].rename(columns={cand[0]:'dangerous'})
wide=df.pivot_table(index='pair_id', columns='group', values='dangerous', aggfunc='first').reset_index().dropna(subset=['ru','eu'])
wide['pair_min']=wide[['ru','eu']].min(axis=1)
wide['pair_max']=wide[['ru','eu']].max(axis=1)
wide=wide.sort_values(['pair_min','pair_max'], ascending=[True,True]).reset_index(drop=True)
y=np.arange(len(wide))
ru_color, eu_color='#3852B4','#FF8C00'
fig, ax=plt.subplots(figsize=(10.8,8.0))
ax.barh(y, -wide['ru'], color=ru_color, height=0.8, label='RU')
ax.barh(y, wide['eu'], color=eu_color, height=0.8, label='EU')
for i,row in enumerate(wide.itertuples(index=False)):
    ax.text(-row.ru-0.5,i,f'{int(row.ru)}',va='center',ha='right',fontsize=9,color=ru_color)
    ax.text(row.eu+0.5,i,f'{int(row.eu)}',va='center',ha='left',fontsize=9,color=eu_color)
ax.axvline(0,color='#455A64',linewidth=1)
maxv=int(max(wide['ru'].max(), wide['eu'].max())+2)
ticks=np.arange(-maxv,maxv+1,5)
ax.set_xticks(ticks); ax.set_xticklabels([str(abs(int(t))) for t in ticks])
ax.set_yticks(y); ax.set_yticklabels([PAIR_LABELS.get(p,p) for p in wide['pair_id']], fontsize=10)
ax.set_xlabel('Dangerous permissions count', fontsize=11)
ax.set_title('Dangerous permissions per matched pair (mirrored view)', fontsize=14, pad=12)
ax.grid(axis='x', linestyle=':', linewidth=0.8, alpha=0.18)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
ax.legend(frameon=False, loc='lower right')
fig.tight_layout()
out=OUT/'fig6_2_dangerous_permissions_mirrored.png'; fig.savefig(out,dpi=300,bbox_inches='tight'); print(out)
