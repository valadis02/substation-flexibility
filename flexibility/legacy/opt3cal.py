import pandas as pd, numpy as np
# --- rolling (honest, forward) Option 3: conformal calibration like Option 2
f3=pd.read_csv("fc3_hourly.csv",index_col=0,parse_dates=True)
lo=np.minimum(f3['qC_0.05'],f3['qC_0.95']); hi=np.maximum(f3['qC_0.05'],f3['qC_0.95'])
s=np.maximum(lo-f3.actual,f3.actual-hi); f3['cq3']=np.nan
for D in pd.date_range("2026-09-20","2026-10-15",freq="D",tz="UTC"):
    past=s[(f3.index<D)&(f3.index>=D-pd.Timedelta(days=14))]
    if len(past)>=72: f3.loc[(f3.index>=D)&(f3.index<D+pd.Timedelta(days=1)),'cq3']=np.quantile(past,0.9)
f3['o3c_lo']=lo-f3.cq3; f3['o3c_hi']=hi+f3.cq3
f3.to_csv("fc3_hourly.csv")
c=f3[(f3.index>="2026-10-01")&f3.cq3.notna()]
print("rolling 1-15/10 cov",round(100*((c.actual>=c.o3c_lo)&(c.actual<=c.o3c_hi)).mean(),1),"width",round((c.o3c_hi-c.o3c_lo).mean(),2))
# --- leave-one-day-out (for hot days): calibrate with other days' scores
R=pd.read_csv("opt3_hourly.csv",index_col=0,parse_dates=True)
lo=np.minimum(R['q0.05'],R['q0.95']); hi=np.maximum(R['q0.05'],R['q0.95']); s=np.maximum(lo-R.actual,R.actual-hi)
R['cq']=np.nan
for D in pd.unique(R.index.normalize()):
    m=R.index.normalize()==D; R.loc[m,'cq']=np.quantile(s[~m],0.9)
R['c_lo']=lo-R.cq; R['c_hi']=hi+R.cq
R.to_csv("opt3_hourly.csv")
print("LOO cov",round(100*((R.actual>=R.c_lo)&(R.actual<=R.c_hi)).mean(),1),"width",round((R.c_hi-R.c_lo).mean(),2))
dm=R.temp.resample('1D').mean(); print("hottest days:",dm.sort_values(ascending=False).head(4).round(1).to_dict())
