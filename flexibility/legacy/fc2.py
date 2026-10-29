import pandas as pd, numpy as np, glob, sys, warnings; warnings.filterwarnings("ignore")
from sklearn.ensemble import HistGradientBoostingRegressor as HGB
fs=glob.glob(sys.argv[1]+"/*house_*.csv")
df=pd.concat([pd.read_csv(f) for f in fs]); df['timestamp']=pd.to_datetime(df.timestamp,utc=True)
W=df.pivot(index='timestamp',columns='house_id',values='consumption').interpolate(limit_direction='both')/1000
y=W.sum(axis=1)
idx=y.index; day=idx.normalize()
def daylag(s,k): return s.shift(24*k)
# ---- feature set A (previous experiment)
A=pd.DataFrame(index=idx); A['hour']=idx.hour; A['dow']=idx.dayofweek
for k in (1,2,7,14,21,28): A[f'lag{k}d']=daylag(y,k)
L4=A[['lag7d','lag14d','lag21d','lag28d']]
A['mean4w']=L4.mean(axis=1); A['max4w']=L4.max(axis=1); A['min4w']=L4.min(axis=1)
dmean=y.groupby(day).transform('mean')
A['prevday_mean']=daylag(dmean,1)
# ---- feature set B = A + more (all known at 00:00 of target day)
B=A.copy()
for k in (3,4,5,6): B[f'lag{k}d']=daylag(y,k)
B['mean7d_samehour']=B[[f'lag{k}d' for k in range(1,8)]].mean(axis=1)
B['std4w']=L4.std(axis=1)
B['is_weekend']=(idx.dayofweek>=5).astype(int)
dmax=y.groupby(day).transform('max'); dmin=y.groupby(day).transform('min')
B['prevday_max']=daylag(dmax,1); B['prevday_min']=daylag(dmin,1)
B['prev7_mean']=daylag(dmean,1).rolling(24*7,min_periods=24).mean()
B['level_ratio']=B['prev7_mean']/B['mean4w'].groupby(day).transform('mean')   # recent level vs 4w
# occupancy proxy: number of houses whose previous-day mean > 30 W
act=(W.groupby(day).transform('mean')>0.03).sum(axis=1)
B['active_houses']=daylag(act.astype(float),1)
# per-house same-hour yesterday and last week (houses as features)
for h in W.columns:
    B[f'h{h}_lag1d']=daylag(W[h],1); B[f'h{h}_lag7d']=daylag(W[h],7)
B['hour_sin']=np.sin(2*np.pi*idx.hour/24); B['hour_cos']=np.cos(2*np.pi*idx.hour/24)
B['dayofyear']=idx.dayofyear
P=dict(max_iter=400,learning_rate=0.04,max_leaf_nodes=15,min_samples_leaf=20,l2_regularization=1.0,random_state=0)
ok=B.notna().all(axis=1)
T0=pd.Timestamp("2026-09-20",tz="UTC"); T1=pd.Timestamp("2026-10-16",tz="UTC")
days=pd.date_range(T0,T1-pd.Timedelta(days=1),freq="D")
rows=[]
for D in days:  # rolling origin: retrain each day on all data before D
    tr=ok&(idx<D); te=(idx>=D)&(idx<D+pd.Timedelta(days=1))
    out=pd.DataFrame(index=idx[te]); out['actual']=y[te]
    out['naive_1d']=A.loc[te,'lag1d']; out['naive_7d']=A.loc[te,'lag7d']; out['mean4w']=A.loc[te,'mean4w']
    out['gbm_A']=HGB(**P).fit(A[tr],y[tr]).predict(A[te])
    out['gbm_B']=HGB(**P).fit(B[tr],y[tr]).predict(B[te])
    for a in (0.05,0.5,0.95):
        out[f'qB_{a}']=HGB(loss='quantile',quantile=a,**P).fit(B[tr],y[tr]).predict(B[te])
    out['ntrain']=int(tr.sum()); rows.append(out)
R=pd.concat(rows)
# conformal calibration of the 5-95 band: widen by the 90% quantile of past nonconformity (from earlier test days only)
lo=np.minimum(R['qB_0.05'],R['qB_0.95']); hi=np.maximum(R['qB_0.05'],R['qB_0.95'])
s=np.maximum(lo-R.actual,R.actual-hi)
R['cq']=np.nan
for D in days:
    past=s[(R.index<D)&(R.index>=D-pd.Timedelta(days=14))]
    if len(past)>=72: R.loc[(R.index>=D)&(R.index<D+pd.Timedelta(days=1)),'cq']=np.quantile(past,0.9)
R['cal_lo']=lo-R.cq; R['cal_hi']=hi+R.cq; R['raw_lo']=lo; R['raw_hi']=hi
# 4-week min-max (today) band
R['mm_lo']=A.loc[R.index,'min4w']; R['mm_hi']=A.loc[R.index,'max4w']
L=pd.read_csv("backtest_hourly.csv",parse_dates=["ts"]).set_index("ts"); R['lstm']=L['fc_sum_houses'].reindex(R.index)/1000
R.to_csv("fc2_hourly.csv")
def met(sub,c):
    e=sub[c]-sub.actual; return pd.Series({'nMAE_%':100*e.abs().mean()/sub.actual.mean(),'RMSE_kW':np.sqrt((e**2).mean()),'MAE_kW':e.abs().mean()})
print("rows",len(R),"days",len(days),"train rows first/last",R.ntrain.iloc[0],R.ntrain.iloc[-1])
M=pd.DataFrame({c:met(R,c) for c in ['naive_1d','naive_7d','mean4w','gbm_A','gbm_B','qB_0.5']}).T; print(M.round(3))
sub=R[R.lstm.notna()]; print("Oct1-15 subset:"); print(pd.DataFrame({c:met(sub,c) for c in ['lstm','mean4w','gbm_A','gbm_B','qB_0.5']}).T.round(3))
c=R[R.cq.notna()]
def cov(d,l,h): return 100*((d.actual>=d[l])&(d.actual<=d[h])).mean(), (d[h]-d[l]).mean()
print("bands on days with calibration (n=%d):"%len(c)); 
for n,(l,h) in {'min-max 4w':('mm_lo','mm_hi'),'quantile 5-95 raw':('raw_lo','raw_hi'),'quantile 5-95 calibrated':('cal_lo','cal_hi')}.items(): print(n, [round(v,2) for v in cov(c,l,h)])
M.to_csv("fc2_metrics.csv")
