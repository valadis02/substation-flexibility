import pandas as pd, numpy as np, sys, warnings; warnings.filterwarnings("ignore")
src=sys.argv[1]; wx=sys.argv[2]
exec(open("fc2.py").read().split("P=dict")[0].replace("sys.argv[1]","src"))
w=pd.read_csv(wx,skiprows=3); w.columns=['time','temp','rh','cloud','rad','is_day']
w.index=pd.to_datetime(w.time).dt.tz_localize("UTC"); w=w.drop(columns='time').reindex(idx)
def wfeat(w):
    F=pd.DataFrame(index=idx)
    F['temp']=w.temp; F['rh']=w.rh; F['cloud']=w.cloud; F['rad']=w.rad; F['is_day']=w.is_day
    F['temp_day_mean']=w.temp.groupby(day).transform('mean')          # forecastable daily mean
    F['temp_day_max']=w.temp.groupby(day).transform('max')
    F['temp_prevday_mean']=w.temp.groupby(day).transform('mean').shift(24)
    F['cdd']=np.maximum(w.temp-24,0); F['hdd']=np.maximum(16-w.temp,0)
    F['temp_lag3h']=w.temp.shift(3)
    return F
hol=pd.to_datetime(["2026-08-15"]).date
C=pd.concat([B,wfeat(w)],axis=1); C['holiday']=np.isin(idx.date,hol).astype(int)
P=dict(max_iter=400,learning_rate=0.04,max_leaf_nodes=15,min_samples_leaf=20,l2_regularization=1.0,random_state=0)
ok=C.notna().all(axis=1)
days=pd.date_range("2026-09-20","2026-10-15",freq="D",tz="UTC")
R=pd.read_csv("fc2_hourly.csv",index_col=0,parse_dates=True)
neutral=w.copy(); neutral['temp']=20.0
Cn=pd.concat([B,wfeat(neutral)],axis=1); Cn['holiday']=C['holiday']
for col in ['qC_0.5','qC_0.05','qC_0.95','thermal']: R[col]=np.nan
for D in days:
    tr=ok&(idx<D); te=(idx>=D)&(idx<D+pd.Timedelta(days=1)); ri=idx[te]
    m=HGB(loss='quantile',quantile=0.5,**P).fit(C[tr],y[tr])
    R.loc[ri,'qC_0.5']=m.predict(C[te])
    R.loc[ri,'thermal']=m.predict(C[te])-m.predict(Cn[te])
    for a in (0.05,0.95): R.loc[ri,f'qC_{a}']=HGB(loss='quantile',quantile=a,**P).fit(C[tr],y[tr]).predict(C[te])
R['temp']=w.temp.reindex(R.index)
nm=lambda c: 100*(R[c]-R.actual).abs().mean()/R.actual.mean()
print({c:round(nm(c),1) for c in ['mean4w','qB_0.5','qC_0.5']})
d=R.groupby(R.index.date).apply(lambda g: pd.Series({c:(g[c]-g.actual).abs().mean() for c in ['qB_0.5','qC_0.5']}))
print("days C better than B:",(d['qC_0.5']<d['qB_0.5']).sum(),"/",len(d))
lo=np.minimum(R['qC_0.05'],R['qC_0.95']); hi=np.maximum(R['qC_0.05'],R['qC_0.95']); print("C 5-95 cov",round(100*((R.actual>=lo)&(R.actual<=hi)).mean(),1),"width",round((hi-lo).mean(),2))
# thermal component on the full history fit (for the Aug-Oct picture): train on all data, counterfactual
mall=HGB(loss='quantile',quantile=0.5,**P).fit(C[ok],y[ok])
TH=pd.DataFrame({'y':y,'pred':pd.Series(np.nan,index=idx),'neutral':np.nan,'temp':w.temp},index=idx)
TH.loc[ok,'pred']=mall.predict(C[ok]); TH.loc[ok,'neutral']=mall.predict(Cn[ok]); TH['thermal']=TH.pred-TH.neutral
TH.to_csv("thermal_all.csv"); R.to_csv("fc3_hourly.csv")
dd=TH.dropna().resample('1D').mean()
print("corr daily cons vs daily temp:",round(dd.y.corr(dd.temp),2))
print("thermal share by month:",(TH.dropna().groupby(TH.dropna().index.month).apply(lambda g:100*g.thermal.clip(lower=0).sum()/g.y.sum())).round(1).to_dict())
print("thermal kW mean by month:",TH.dropna().groupby(TH.dropna().index.month).thermal.mean().round(2).to_dict())
