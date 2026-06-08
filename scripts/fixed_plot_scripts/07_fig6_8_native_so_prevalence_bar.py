
import pandas as pd, matplotlib.pyplot as plt
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Plots' / 'thesis_plot_scripts_projectpaths'; OUT.mkdir(parents=True, exist_ok=True)
df=pd.read_csv(ROOT/'results/native/native_libs_per_app.csv')
df['has_native_so']=df['native_so_count_total'].fillna(0)>0
summary=df.groupby('region',as_index=False)['has_native_so'].mean()
summary['region']=summary['region'].str.lower(); summary['percent']=summary['has_native_so']*100
summary['region']=pd.Categorical(summary['region'],categories=['ru','eu'],ordered=True); summary=summary.sort_values('region')
labels=['RU applications','EU applications']; colors=['#0046FF','#F25912']
fig,ax=plt.subplots(figsize=(7.2,4.8))
bars=ax.bar(labels, summary['percent'], color=colors, width=0.58)
ax.tick_params(axis='y', labelsize=14)
ax.tick_params(axis='x', labelsize=14)
for bar,val in zip(bars, summary['percent']):
    ax.text(bar.get_x()+bar.get_width()/2, val+0.8, f'{val:.1f}%', ha='center', fontsize=14)
ax.set_ylabel('Applications with at least one native .so library (%)', fontsize=12)
ax.set_ylim(0,50)
ax.set_title('Prevalence of native .so libraries in RU and EU applications', fontsize=14, pad=10)
ax.grid(axis='y', linestyle=':', linewidth=0.8, alpha=0.18)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
fig.tight_layout(); out=OUT/'fig6_8_native_so_prevalence_bar.png'; fig.savefig(out,dpi=300,bbox_inches='tight'); print(out)
