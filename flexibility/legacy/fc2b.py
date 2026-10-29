exec(open("fc2.py").read().split("P=dict")[0])
P=dict(max_iter=400,learning_rate=0.04,max_leaf_nodes=15,min_samples_leaf=20,l2_regularization=1.0,random_state=0)
R=pd.read_csv("fc2_hourly.csv",index_col=0,parse_dates=True)
okA=A.notna().all(axis=1); qa=[]
for D in pd.date_range("2026-09-20","2026-10-15",freq="D",tz="UTC"):
    tr=okA&(idx<D); te=(idx>=D)&(idx<D+pd.Timedelta(days=1))
    qa.append(pd.Series(HGB(loss='quantile',quantile=0.5,**P).fit(A[tr],y[tr]).predict(A[te]),index=idx[te]))
R['qA_0.5']=pd.concat(qa)
for c in ['mean4w','qA_0.5','qB_0.5']: print(c, round(100*(R[c]-R.actual).abs().mean()/R.actual.mean(),1))
d=R.groupby(R.index.date).apply(lambda g: pd.Series({c:(g[c]-g.actual).abs().mean() for c in ['mean4w','naive_1d','qB_0.5']}))
print("days qB better than mean4w:",(d['qB_0.5']<d['mean4w']).sum(),"/",len(d), " better than naive_1d:",(d['qB_0.5']<d['naive_1d']).sum())
R.to_csv("fc2_hourly.csv")
