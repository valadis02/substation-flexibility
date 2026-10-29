import pandas as pd, numpy as np, glob, sys, warnings; warnings.filterwarnings("ignore")
from sklearn.ensemble import HistGradientBoostingRegressor as HGB
src,wx=sys.argv[1],sys.argv[2]
df=pd.concat([pd.read_csv(f) for f in glob.glob(src+"/*house_*.csv")]); df['timestamp']=pd.to_datetime(df.timestamp,utc=True)
W=df.pivot(index='timestamp',columns='house_id',values='consumption').interpolate(limit_direction='both')/1000
idx=W.index; loc=idx.tz_convert("Europe/Athens"); day=loc.normalize()
w=pd.read_csv(wx,skiprows=3); w.columns=['time','temp','rh','cloud','rad','is_day']; w.index=pd.to_datetime(w.time).dt.tz_localize("UTC"); w=w.drop(columns='time').reindex(idx)
def feats(s,temp):
    F=pd.DataFrame(index=idx); F['hour']=loc.hour; F['dow']=loc.dayofweek; F['wkend']=(loc.dayofweek>=5).astype(int)
    for k in (1,7,14): F[f'l{k}']=s.shift(24*k)
    F['m4']=pd.concat([s.shift(24*7*k) for k in (1,2,3,4)],axis=1).median(axis=1)
    F['temp']=temp; F['tday']=pd.Series(temp,index=idx).groupby(day).transform('mean').values
    F['cdd']=np.maximum(temp-24,0); F['rad']=w.rad.values; F['cloud']=w.cloud.values; F['is_day']=w.is_day.values
    return F
P=dict(max_iter=300,learning_rate=0.05,max_leaf_nodes=15,min_samples_leaf=30,l2_regularization=1.0,random_state=0)
MEAL=lambda h: ((h>=12)&(h<15))|((h>=18)&(h<22))
comp={}
for h in W.columns:
    s=W[h]; F=feats(s,w.temp.values); Fn=feats(s,np.full(len(idx),20.0)); ok=F.notna().all(axis=1)
    m=HGB(loss='quantile',quantile=0.5,**P).fit(F[ok],s[ok])
    pred=pd.Series(np.nan,index=idx); neu=pred.copy(); pred[ok]=m.predict(F[ok]); neu[ok]=m.predict(Fn[ok])
    night=s[(loc.hour>=2)&(loc.hour<6)]
    base=night.groupby(night.index.tz_convert("Europe/Athens").normalize()).quantile(0.1).rolling(7,min_periods=3).median()
    base=pd.Series(base.reindex(day).values,index=idx).bfill()
    thermal=(pred-neu).clip(lower=0)
    exc=(s-pred); ev=exc.where(exc>0.4,0.0)          # discrete large events above the house's own expected load
    meal=MEAL(loc.hour)&(loc.dayofweek<5)
    ev_meal=ev.where(meal,0.0); ev_shift=ev.where(~meal,0.0)
    routine=(s-base-thermal-ev).clip(lower=0)
    comp[h]=pd.DataFrame({'actual':s,'base':np.minimum(base,s),'thermal':thermal,'ev_shift':ev_shift,'ev_meal':ev_meal,'routine':routine,'ok':ok})
A=sum(c[['actual','base','thermal','ev_shift','ev_meal','routine']] for c in comp.values())
A=A[comp[W.columns[0]].ok]; A.index=A.index.tz_convert("Europe/Athens"); A.to_csv("decomp_agg.csv")
A['resid']=A.actual-A[['base','thermal','ev_shift','ev_meal','routine']].sum(axis=1)
hot=A[A.index<pd.Timestamp("2026-09-20",tz="Europe/Athens")]; cool=A[A.index>=pd.Timestamp("2026-09-20",tz="Europe/Athens")]
for n,d in (("hot",hot),("cool",cool)):
    sh=100*d[['base','thermal','ev_shift','ev_meal','routine','resid']].sum()/d.actual.sum(); print(n,sh.round(1).to_dict())
    g=d.groupby(d.index.hour)[['thermal','ev_shift']].mean().sum(axis=1)
    print("  shiftable kW 18-23:",round(g.loc[18:22].mean(),2)," 12-15:",round(g.loc[12:14].mean(),2)," total load 18-23:",round(d[d.index.hour.isin(range(18,23))].actual.mean(),2))
# ---- consistent version: thermal from the aggregate leave-one-day-out model, sequential allocation (sums to actual)
R=pd.read_csv("opt3_hourly.csv",index_col=0,parse_dates=True); thA=(R['q0.5']-R['n0.5']).clip(lower=0); thA.index=thA.index.tz_convert("Europe/Athens")
S=sum(c[['actual','base','ev_shift','ev_meal']] for c in comp.values()); S.index=S.index.tz_convert("Europe/Athens")
S=S.loc[thA.index]
out=pd.DataFrame(index=S.index); rem=S.actual.copy()
for name,val in (('base',S.base),('thermal',thA),('ev_shift',S.ev_shift),('ev_meal',S.ev_meal)):
    a=np.minimum(val.clip(lower=0),rem); out[name]=a; rem=rem-a
out['routine']=rem; out['actual']=S.actual; out.to_csv("decomp_agg2.csv")
hot=out[out.index<pd.Timestamp("2026-09-20",tz="Europe/Athens")]; cool=out[out.index>=pd.Timestamp("2026-09-20",tz="Europe/Athens")]
print("---- consistent")
for n,d in (("hot",hot),("cool",cool)):
    sh=100*d[['base','thermal','ev_shift','ev_meal','routine']].sum()/d.actual.sum(); print(n,sh.round(1).to_dict())
    g=d.groupby(d.index.hour)[['thermal','ev_shift']].mean()
    for lab,hrs in (("18-23",range(18,23)),("12-15",range(12,15)),("02-06",range(2,6))):
        print(f"  {lab}: thermal {g.loc[list(hrs)].thermal.mean():.2f} kW · shiftable events {g.loc[list(hrs)].ev_shift.mean():.2f} kW · load {d[d.index.hour.isin(hrs)].actual.mean():.2f} kW")
