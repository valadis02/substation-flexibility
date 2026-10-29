"""HISTORICAL: ran with method v0.3-v0.4 (gradient-boosting M2 with a neutral-temperature counterfactual), which was
removed in v0.5. Results are in experiments/RESULTS.md; to rerun, check out the commit that added this script.
"""
"""T2 diagnostic: thermal share with and without the clip at 0 (T0 = 20, full model, leave-one-week-out), per Plegma development home."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '.')
from sklearn.ensemble import HistGradientBoostingRegressor as HGB
from flexsub import Config, features, splits
from flexsub.data import load_processed
cfg=Config(tz="Europe/Athens")
d=load_processed('data/processed/plegma'); Wd=splits.development(d['W'],'plegma')
out=[]
for h in Wd.columns:
    y=Wd[h]
    if y.notna().sum()<24*60: continue
    y=y[y.first_valid_index():y.last_valid_index()].asfreq('1h'); w=d['weather'].reindex(y.index)
    A=d['appliances'][h].reindex(y.index); acc=[c for c in A if c.startswith('ac')]
    tr_=A[acc].sum(axis=1,min_count=len(acc)) if acc else pd.Series(0.0,index=y.index)
    y.index=y.index.tz_convert(cfg.tz); w.index=w.index.tz_convert(cfg.tz); tr_.index=y.index
    X=features.build(y,w,cfg); Xn=features.build(y,w,cfg,neutral=True)[X.columns]
    ok=(y.notna()&X['lag7d'].notna()).to_numpy()
    wk=((y.index.tz_localize(None).normalize()-y.index[0].tz_localize(None).normalize()).days//7).to_numpy()
    e=np.full(len(y),np.nan)
    for k in np.unique(wk[ok]):
        te=ok&(wk==k); tr=ok&(wk!=k)
        m=HGB(loss='quantile',quantile=0.5,**cfg.gbm).fit(X[tr],y[tr])
        e[te]=m.predict(X[te])-m.predict(Xn[te])
    e=pd.Series(e,index=y.index); v=e.notna()&tr_.notna()
    dd=y.index.normalize()
    ed=e[v].groupby(dd[v]).sum(); td=tr_[v].groupby(dd[v]).sum()
    out.append(dict(home=h,ac=bool(acc),share_true=tr_[v].sum()/y[v].sum(),share_raw=e[v].sum()/y[v].sum(),share_clip=e[v].clip(lower=0).sum()/y[v].sum(),
        corr_daily_raw=np.corrcoef(ed,td)[0,1] if td.std()>0 else np.nan, corr_daily_clipsum=np.corrcoef(e[v].clip(lower=0).groupby(dd[v]).sum(),td)[0,1] if td.std()>0 else np.nan))
    print(out[-1],flush=True)
print(pd.DataFrame(out).round(3).to_string())
