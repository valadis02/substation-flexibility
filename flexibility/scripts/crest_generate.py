"""Synthetic UK households with the CREST/Richardson model (richardsonpy), per appliance, 1-minute, with reactive power.

Used to reproduce Ponocko & Milanovic (2018), whose main results are on 1,000 CREST households, and to compare their
method with ours on the same data. Q per appliance = P x tan(arccos(mean power factor)) from the model's appliance
table; lighting PF taken as 1 (incandescent/CFL mix is not separated in richardsonpy - stated deviation).

    python scripts/crest_generate.py --homes 1000 --days 60 --start-day 1 --seed 1 --out data/crest
Output (not committed, regenerate with the same seed): <out>/appliances_1min_<home>.npz is avoided for size;
instead per home the hourly kW per appliance and the 1-minute aggregate P, Q are stored:
  <out>/homes_hourly.parquet-like CSV.gz per home (appliance kW hourly), <out>/agg_1min.npz (P, Q of all homes summed)
"""
import argparse, os, time, random
import numpy as np
import pandas as pd
import richardsonpy.classes.occupancy as occ_mod
import richardsonpy.classes.appliance as app_mod
import richardsonpy.classes.lighting as light_mod
import richardsonpy.classes.stochastic_el_load_wrapper as wrap
import richardsonpy.functions.load_radiation as loadrad

# Fix a richardsonpy bug: the activity table has 6 activity profiles per active-occupant count (TV, cooking, laundry,
# wash/dress, iron, house clean), but run_application_simulation indexes it with 5 * occupants + profile, so e.g.
# laundry with 2 active occupants reads the TV row (wet appliances ~2-3x too often). CREST (VBA) uses 6.
import inspect, textwrap
_src = inspect.getsource(app_mod.run_application_simulation)
assert "int(5 * iActiveOccupants + sUseProfile)" in _src
exec(compile(textwrap.dedent(_src.replace("int(5 * iActiveOccupants + sUseProfile)", "int(6 * iActiveOccupants + sUseProfile)")),
             app_mod.__file__, "exec"), app_mod.__dict__)

ap = argparse.ArgumentParser()
ap.add_argument("--homes", type=int, default=1000)
ap.add_argument("--days", type=int, default=60)
ap.add_argument("--start-day", type=int, default=1, help="day of year of the first day (1 = 1 Jan)")
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--first", type=int, default=0, help="first home id (to split the run over processes)")
ap.add_argument("--out", default="data/crest")
ap.add_argument("--calib-one", action="store_true", help="use calibration factor 1 instead of richardsonpy's demand calibration")
a = ap.parse_args()
random.seed(a.seed); np.random.seed(a.seed)
src = os.path.dirname(app_mod.__file__).replace("classes", "")
tab = pd.read_csv(os.path.join(src, "inputs", "Appliances.csv"), sep=";", header=0)
names = tab.iloc[:, 1].astype(str).tolist()
pf = tab.iloc[:, -1].astype(float).clip(0.3, 1.0).to_numpy()
tanphi = np.tan(np.arccos(pf))
# Ponocko & Milanovic (2018), Table I: load categories. Controllable = CTIM1 + QTIM1 + RC.
PM = {"CTIM1": ["Dish washer", "Tumble dryer", "Washing machine", "Washer dryer", "Vacuum"],
      "QTIM1": ["Chest freezer", "Fridge freezer", "Refrigerator", "Upright freezer"],
      "RC": ["DESWH", "E-INST", "Electric shower", "Storage heaters", "Other electric space heating"],
      "RUC": ["Iron", "Hob", "Oven", "Kettle", "Small cooking (group)"],
      "SMPS": ["Answer machine", "Cassette / CD Player", "Clock", "Cordless telephone", "Hi-Fi", "Fax", "Personal computer",
               "Printer", "TV 1", "TV 2", "TV 3", "VCR / DVD", "TV Receiver box", "Microwave"]}
CAT = ["CTIM1", "QTIM1", "RC", "RUC", "SMPS", "Lighting"]
groups = [next(k for k, v in PM.items() if n in v) for n in names]   # kettle / small cooking: resistive, not controllable -> RUC
(q_dir, q_dif) = loadrad.get_rad_from_try_path()   # hourly (German TRY; only drives lighting)
irr_year = (q_dir + q_dif)
os.makedirs(a.out, exist_ok=True)
t0 = time.time()
meta = []
for h in range(a.first, a.first + a.homes):
    random.seed(a.seed * 100003 + h); np.random.seed(a.seed * 100003 + h)   # each home reproducible on its own
    n_occ = int(np.random.choice([1, 2, 3, 4, 5], p=[0.29, 0.35, 0.16, 0.14, 0.06]))   # UK occupancy (Ponocko & Milanovic, Sec. V)
    occ = occ_mod.Occupancy(number_occupants=n_occ, initial_day=1 + (a.start_day - 1) % 7, nb_days=a.days)
    from richardsonpy.classes.electric_load import ElectricLoad
    std = ElectricLoad.standard_consumption["SFH"][n_occ] * 0.91
    appliances = app_mod.Appliances(os.path.join(src, "inputs", "Appliances.csv"), annual_consumption=std, randomize_appliances=True)
    if a.calib_one:   # original CREST: calibration factor 1 (cycles per year as in the appliance table)
        appliances.estimate_annual_consumption(1.0)
    lights = light_mod.load_lighting_profile(filename=os.path.join(src, "inputs", "LightBulbs.csv"), index=random.randint(0, 99))
    w = wrap.ElectricityProfile(appliances, lights)
    per_app = np.zeros((len(names), a.days * 1440)); light = np.zeros(a.days * 1440)
    for d in range(a.days):
        doy = a.start_day - 1 + d
        weekend = (d + a.start_day - 1) % 7 in (5, 6)
        irr = np.interp(np.arange(1440), 60 * np.arange(24), irr_year[24 * doy: 24 * (doy + 1)])
        o = occ.occupancy[144 * d: 144 * (d + 1)]
        tot, lp, appp = None, None, None
        month = w._get_month(doy)
        dl = light_mod.run_lighting_simulation(vOccupancyArray=o, vBulbArray=lights, vIrradianceArray=irr,
                                               light_mod_config=w.lighting_config)
        da = app_mod.run_application_simulation(o, appliances, w.activity_statistics["we" if weekend else "wd"], month)
        per_app[:, 1440 * d: 1440 * (d + 1)] = np.array(da)[:len(names)]
        light[1440 * d: 1440 * (d + 1)] = np.sum(dl, axis=0)
    P = per_app.sum(axis=0) + light
    Q = (per_app * tanphi[:, None]).sum(axis=0)
    hourly = pd.DataFrame(per_app.reshape(len(names), a.days * 24, 60).mean(axis=2).T / 1000.0, columns=names)
    hourly["lighting"] = light.reshape(a.days * 24, 60).mean(axis=1) / 1000.0
    hourly = hourly.loc[:, hourly.sum() > 0]
    hourly.round(5).to_csv(os.path.join(a.out, f"home_{h:04d}.csv.gz"), index=False)
    np.savez_compressed(os.path.join(a.out, f"home_{h:04d}_1min.npz"), P=P.astype(np.float32), Q=Q.astype(np.float32),
                        per_cat=np.stack([per_app[[j for j, g in enumerate(groups) if g == c]].sum(axis=0) for c in CAT[:-1]] + [light]).astype(np.float16),
                        cat_names=np.array(CAT))
    meta.append(dict(home=h, occupants=n_occ, kwh_day=float(P.sum() / 60 / 1000 / a.days)))
    if h % 10 == 0:
        print(h, f"{time.time() - t0:.0f}s", meta[-1], flush=True)
pd.DataFrame(meta).to_csv(os.path.join(a.out, f"homes_{a.first:04d}.csv"), index=False)
print("done", f"{time.time() - t0:.0f}s")
