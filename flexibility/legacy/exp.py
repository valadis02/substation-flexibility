import pandas as pd, numpy as np, glob, sys, itertools, json
rng=np.random.default_rng(0)
fs=glob.glob(sys.argv[1]+"/*house_*.csv")
df=pd.concat([pd.read_csv(f) for f in fs]); df['timestamp']=pd.to_datetime(df.timestamp,utc=True)
W=df.pivot(index='timestamp',columns='house_id',values='consumption').interpolate(limit_direction='both')
houses=list(W.columns)
W['date']=W.index.date; W['hour']=W.index.hour
dates=sorted(set(W.date)); full=[d for d in dates if (W.date==d).sum()==24]
# target days with 28 days history (FLEXiT: last 30 dates before D, same weekday -> D-7,-14,-21,-28)
targets=[d for d in full if pd.Timestamp(d)-pd.Timedelta(days=28)>=pd.Timestamp(dates[0])]
arr={h:W.pivot_table(index='date',columns='hour',values=h) for h in houses}  # date x hour
def past_vals(h_list,D):
    ds=[(pd.Timestamp(D)-pd.Timedelta(days=k)).date() for k in (7,14,21,28)]
    return np.stack([arr[h].loc[ds].values for h in h_list])  # houses x 4 x 24
rows=[]
for N in (1,2,5,10):
    combos=list(itertools.combinations(houses,N))
    if len(combos)>40: combos=[tuple(rng.choice(houses,N,replace=False)) for _ in range(40)]
    for c in combos:
        for D in targets:
            P=past_vals(c,D); real=np.stack([arr[h].loc[D].values for h in c])
            base_i=P.mean(1); mx_i=P.max(1); mn_i=P.min(1)
            S=P.sum(0); rs=real.sum(0)
            base=base_i.sum(0)
            up_sum=(mx_i-base_i).sum(0); dn_sum=(base_i-mn_i).sum(0)   # sum of envelopes
            up_agg=S.max(0)-base; dn_agg=base-S.min(0)                   # envelope of sum
            for hr in range(24):
                rows.append(dict(N=N,combo=str(c),date=str(D),hour=hr,base=base[hr],
                  up_sum=up_sum[hr],dn_sum=dn_sum[hr],up_agg=up_agg[hr],dn_agg=dn_agg[hr],real=rs[hr],
                  in_agg=(S.min(0)[hr]<=rs[hr]<=S.max(0)[hr]),
                  in_sum=(mn_i.sum(0)[hr]<=rs[hr]<=mx_i.sum(0)[hr]),
                  in_each=bool(np.all((mn_i[:,hr]<=real[:,hr])&(real[:,hr]<=mx_i[:,hr])))))
R=pd.DataFrame(rows); R.to_csv("results_long.csv",index=False)
g=R.groupby('N')
summ=pd.DataFrame({
 'combos':g.combo.nunique(),'target_days':g.date.nunique(),
 'base_W_mean':g.base.mean(),
 'up_sum_W':g.up_sum.mean(),'up_agg_W':g.up_agg.mean(),
 'ratio_up(agg/sum)':g.up_agg.sum()/g.up_sum.sum(),
 'dn_sum_W':g.dn_sum.mean(),'dn_agg_W':g.dn_agg.mean(),
 'ratio_dn(agg/sum)':g.dn_agg.sum()/g.dn_sum.sum(),
 'EFIup_sum_%':100*g.up_sum.sum()/g.base.sum(),'EFIup_agg_%':100*g.up_agg.sum()/g.base.sum(),
 'cover_agg_%':100*g.in_agg.mean(),'cover_sum_%':100*g.in_sum.mean(),'cover_each_house_%':100*g.in_each.mean()})
print(summ.round(2).T.to_string()); summ.to_csv("summary_by_N.csv")
print("targets",targets[0],"->",targets[-1])
# per-hour ratio for N=10
h=R[R.N==10].groupby('hour')[['up_agg','up_sum','dn_agg','dn_sum','base']].mean()
h['ratio_up']=h.up_agg/h.up_sum; h['ratio_dn']=h.dn_agg/h.dn_sum
print(h.round(2).to_string()); h.to_csv("n10_by_hour.csv")
