
import pandas as pd, numpy as np, matplotlib.pyplot as plt
from pathlib import Path
from matplotlib.colors import TwoSlopeNorm, LinearSegmentedColormap
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Plots' / 'thesis_plot_scripts_projectpaths'; OUT.mkdir(parents=True, exist_ok=True)
df=pd.read_csv(ROOT/'dataset2/dataset2.csv')
appcol='apk_filename'
metrics=['pair_diff_activities_all','pair_diff_activities_exported','pair_diff_services_all','pair_diff_services_exported',
         'pair_diff_receivers_all','pair_diff_receivers_exported','pair_diff_providers_all','pair_diff_providers_exported']
avail=[c for c in metrics if c in df.columns]
play_rows=df[df['store'].astype(str).str.contains('Google Play', case=False, na=False)].copy()
mat=play_rows[[appcol]+avail].copy().rename(columns={c:c.replace('pair_diff_','') for c in avail})
mat[appcol]=mat[appcol].astype(str).str.replace('.apk','', regex=False)
mat=mat.set_index(appcol)
cmap=LinearSegmentedColormap.from_list('cust', ['#5CB338','#ECE852','#FB4141'], N=256)
norm=TwoSlopeNorm(vmin=-10, vcenter=0, vmax=80)
fig,ax=plt.subplots(figsize=(11,7))
im=ax.imshow(mat.values, aspect='auto', cmap=cmap, norm=norm)
for i in range(mat.shape[0]):
    for j in range(mat.shape[1]):
        ax.text(j,i,f'{int(mat.iloc[i,j])}',ha='center',va='center',fontsize=9,color='black')
ax.set_yticks(np.arange(mat.shape[0])); ax.set_yticklabels(mat.index, fontsize=10)
ax.set_xticks(np.arange(mat.shape[1])); ax.set_xticklabels(mat.columns, rotation=35, ha='right', fontsize=10)
ax.set_title('Cross-store component differences (Google Play - RuStore)', fontsize=14, pad=10)
cbar=fig.colorbar(im, ax=ax); cbar.set_label('Difference in count', fontsize=11)
fig.tight_layout(); out=OUT/'fig6_16_to_23_store_components_heatmap.png'; fig.savefig(out,dpi=300,bbox_inches='tight'); print(out)
