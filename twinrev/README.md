# TWIN-REV scenarios: what-if EV / PV adoption on an LV substation (OpenAIFlex Task 1.1)

A digital twin of one LV substation runs inside TWIN-REV (Crete-Valley/TwinRev). This service builds what-if
scenarios, for example "what if twice as many homes had an EV" or "what if every home had PV". It sends each
scenario to TWIN-REV's DSO pipeline, where the DPsim service runs the power flows. It then reports whether the
grid stays within limits.

| | |
|---|---|
| Grid | IEEE European LV test feeder: public, 11/0.4 kV, 800 kVA, 55 customers. In TWIN-REV it is DSO cell 3. |
| Homes | Pecan Street Austin, 25 homes, hourly. The data stays local and is never committed (Dataport licence). The 55 load points are filled with the 25 real homes on the studied day plus the same homes on other weeks (same weekday). Every unit is therefore a real metered home-day. |
| Days | `peak` = the day with the highest substation net load. `pv` = the day with the lowest (most reverse flow). Specific dates can also be given. |
| Scenarios (default) | `today` (as in the data), `ev_x2` (2x the EV share), `ev_all` (EV in every home), `pv_x2` (2x the PV share), `ev_x2_pv_x2`. |
| Hosting capacity | Bisection over DPsim runs: the most EV homes (peak day), the most PV homes (PV day), and, with PV on every home, the largest PV size multiplier (PV day). |
| Limits | V min 0.90 pu and V max 1.10 pu of 400 V (EN 50160), transformer 100 % of 800 kVA. All three can be changed per request. Line current is reported in A only, because the CIM file has no line ratings. |

How the scenarios are built (`service/scenarios.py`):
- **Added EVs**: a home that gets an EV draws a real charging day of an Austin EV home from the 3 weeks around the
  studied day (same weekday or weekend type), so the charging keeps the observed timing and diversity.
- **Added PV**: a home that gets PV gets the median system size times that day's PV shape.
- **Removed EVs**: when a scenario has fewer EVs than the data, the car circuit is subtracted.
- **Seeded order**: the order in which homes get EVs or PV is seeded, so the scenarios are nested (20 EVs includes
  the homes of 10 EVs).
- **Reactive power**: pf 0.95 for consumption.

```
POST /scenarios        {"days": ["peak", "pv"], "scenarios": [{"name": "ev30", "n_ev": 30}], "v_min_pu": 0.90}
                       every field is optional; {} runs the defaults (about 20 power flows, about 2 min)
GET  /scenarios/{id}   status, per day and scenario: V min / V max, transformer %, violations, hosting capacity
GET  /site             the homes, the EV / PV homes in the data, the chosen days, which unit sits on which load point
```
Results go to InfluxDB (database `openaiflex`):
- `lv_scenario,site,day_type,scenario` with `vmin_pu, vmax_pu, trafo_loading_pct, max_line_current_a, net_load_kw`.
  Hours 00-23 of the studied day (Austin local time) are written on 2030-01-01 UTC.
- `lv_hosting,site` with `max_ev_homes, max_pv_homes, max_pv_scale_all_homes`.

Grafana dashboard: `service/grafana_scenarios.json`.

## Setup (single-node SOGNO stack + TWIN-REV in k3s)
Prerequisites:
- SOGNO namespace `sogno` with InfluxDB and Grafana.
- TWIN-REV deployed in namespace `digital-twin` (its smoke test passes).
- The secret `twinrev-db` in `sogno`. It already exists if it was made for the earlier planning test. Otherwise:
```bash
PW=$(kubectl -n digital-twin get secret dt-secrets -o jsonpath='{.data.DB_POST_PASSWORD}' | base64 -d)
kubectl -n sogno create secret generic twinrev-db \
  --from-literal=TWINREV_DB_URL="postgresql+psycopg2://postgres:${PW}@postgres.digital-twin:5432/postgres"
```

**1. The LV feeder in TWIN-REV.** TWIN-REV takes the single `cel3_*.zip` in `dpsim_assets` as cell 3.
```bash
git clone https://github.com/dpsim-simulator/cim-grid-data ~/cim-grid-data
cd ~/substation-flexibility/twinrev
python3 cim/make_lv_zip.py ~/cim-grid-data/IEEE_EU_LV/IEEE_EU_LV_reduced cel3_lv.zip
A=~/TwinRev/digital_twin_backend/fast_api/apisrc/dpsim_assets
rm -f $A/cel3_*.zip && cp cel3_lv.zip $A/             # only one cel3_* archive
cd ~/TwinRev
sudo docker build -t cvdt/dt-backend:local digital_twin_backend/fast_api
sudo docker save cvdt/dt-backend:local | sudo k3s ctr images import -
kubectl -n digital-twin rollout restart deployment/dt-backend
kubectl -n digital-twin rollout status deployment/dt-backend
```

**2. The Austin data (local only).** Download the Austin 15-minute file from Pecan Street Dataport, then run:
```bash
cd ~/substation-flexibility/flexibility
python3 scripts/prepare_data.py pecan_austin /path/to/15minute_data_austin.csv
# -> flexibility/data/processed/pecan_austin/  (git-ignored and docker-ignored)
```
If the real file is not at hand, a **synthetic** stand-in in the same format lets you test the chain. Its numbers
are invented, and `GET /site` then shows `"synthetic": true`.
```bash
python3 twinrev/tests/make_synthetic_austin.py ~/substation-flexibility/flexibility/data/processed/pecan_austin
```

**3. Build and deploy the service.**
```bash
cd ~/substation-flexibility/twinrev
sudo docker build -f service/Dockerfile -t openaiflex/twinrev-scenarios:0.1 .
sudo docker save openaiflex/twinrev-scenarios:0.1 | sudo k3s ctr images import -
sed "s|__AUSTIN_DIR__|$HOME/substation-flexibility/flexibility/data/processed/pecan_austin|" service/k8s.yaml | kubectl apply -f -
kubectl -n sogno rollout status deployment/twinrev-scenarios
kubectl -n sogno port-forward svc/twinrev-scenarios 8002:8000          # http://localhost:8002/docs
```
The data folder is mounted read-only into the pod (hostPath), so no household data is in the image. The manifest also
adds a NetworkPolicy in `digital-twin` that lets this pod reach TWIN-REV's PostgreSQL.

**4. Run.**
```bash
curl -s localhost:8002/site | head -c 600; echo
curl -s -X POST localhost:8002/scenarios -H 'Content-Type: application/json' -d '{}'     # -> {"id": "..."}
curl -s localhost:8002/scenarios/<id>          # repeat until "status": "done"
```
Grafana: Dashboards, then Import, then upload `service/grafana_scenarios.json`, then choose the InfluxDB data
source. Pick the day (`peak` / `pv`) at the top.

## Tests
```bash
cd twinrev && python3 -m pytest -q tests      # scenario construction on synthetic data (no DPsim needed)
```
The full chain was tested on synthetic data:
- DPsim 1.4 with TWIN-REV's DSO router and its dpsv service, IEEE EU LV feeder, 55 units, 22 power flows.
- DPsim on this feeder matches the NEPLAN load flow in the same CIM export within 0.002 V at all 135 nodes.

## Files
- `service/app.py`: API, scenarios, hosting capacity, InfluxDB output.
- `service/scenarios.py`: Austin data and scenario construction.
- `service/grid.py`: profiles into TWIN-REV, pipeline call, voltages and transformer loading.
- `cim/make_lv_zip.py`: IEEE EU LV CIM to TWIN-REV cell-3 archive. Loads are renamed `lod_01..55`, because dpsv
  matches profiles by name prefix.
- `tests/`: synthetic data generator and unit tests.
