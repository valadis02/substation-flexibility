import pandas as pd, numpy as np, sys, warnings; warnings.filterwarnings("ignore")
src,wx=sys.argv[1],sys.argv[2]
exec(open("fc3.py").read().split("\nP=dict(")[0].replace("src=sys.argv[1]; wx=sys.argv[2]",""))
P=dict(max_iter=300,learning_rate=0.05,max_leaf_nodes=15,min_samples_leaf=20,l2_regularization=1.0,random_state=0)
neutral=w.copy(); neutral["temp"]=20.0
Cn=pd.concat([B,wfeat(neutral)],axis=1); Cn["holiday"]=C["holiday"]
ok=C.notna().all(axis=1)
days=pd.date_range("2026-08-30","2026-10-15",freq="D",tz="UTC")
out=[]
for D in days:  # leave-one-day-out: model never sees the day it explains
    te=(idx>=D)&(idx<D+pd.Timedelta(days=1)); tr=ok&~te
    r=pd.DataFrame(index=idx[te]); r['actual']=y[te]; r['temp']=w.temp[te]
    for a in (0.05,0.5,0.95):
        m=HGB(loss='quantile',quantile=a,**P).fit(C[tr],y[tr])
        r[f'q{a}']=m.predict(C[te]); r[f'n{a}']=m.predict(Cn[te])
    out.append(r)
R=pd.concat(out)
for p in ('q','n'):
    lo=np.minimum(R[f'{p}0.05'],R[f'{p}0.95']); hi=np.maximum(R[f'{p}0.05'],R[f'{p}0.95']); med=R[f'{p}0.5'].clip(lo,hi)
    R[f'{p}_up']=hi-med; R[f'{p}_down']=med-lo
R['up_temp']=(R.q_up-R.n_up).clip(lower=0); R['up_other']=R.q_up-R.up_temp
R['down_temp']=(R.q_down-R.n_down).clip(lower=0); R['down_other']=R.q_down-R.down_temp
R['base_temp']=(R['q0.5']-R['n0.5'])
R.to_csv("opt3_hourly.csv")
R.index=R.index.tz_convert("Europe/Athens")
hot=R[R.index<pd.Timestamp("2026-09-20",tz="Europe/Athens")]; cool=R[R.index>=pd.Timestamp("2026-09-20",tz="Europe/Athens")]
for n,d in (("hot",hot),("cool",cool)):
    print(n, "up",round(d.q_up.mean(),3),"of which temp",round(d.up_temp.mean(),3),"| down",round(d.q_down.mean(),3),"of which temp",round(d.down_temp.mean(),3),"| baseline temp part",round(d.base_temp.mean(),3), "cov",round(100*((d.actual>=d['q0.5']-d.q_down)&(d.actual<=d['q0.5']+d.q_up)).mean(),1))
