# TWIN-REV scenarios: what-if EV / PV adoption on an LV substation (OpenAIFlex Task 1.1)

A digital twin of one LV substation runs inside TWIN-REV (Crete-Valley/TwinRev). This service builds what-if
scenarios, for example "what if twice as many homes had an EV" or "what if every home had PV". It sends each
scenario to TWIN-REV's DSO pipeline, where the DPsim service runs the power flows. It then reports whether the
grid stays within limits.

| | |
|---|---|
| Grid | IEEE European LV test feeder (public CIM, 55 customers) as TWIN-REV DSO cell 3, sized for the Austin homes (see below) |
| Homes | Pecan Street Austin, 25 homes, hourly. The data stays local and is never committed (Dataport licence). The 55 load points are filled with the 25 real homes on the studied day plus the same homes on other weeks (same weekday). Every unit is therefore a real metered home-day. |
| Days | `peak` = the day with the highest substation net load. `pv` = the day with the lowest (most reverse flow). Specific dates can also be given. |
| Scenarios (default) | `today` (as in the data), `ev_x2` (2x the EV share), `ev_all` (EV in every home), `pv_x2` (2x the PV share), `ev_x2_pv_x2`. |
| Hosting capacity | Bisection over DPsim runs: the most EV homes (peak day), the most PV homes (PV day), and, with PV on every home, the largest PV size multiplier (PV day). Empty if a limit is already broken today. |
| Limits (planning) | V 0.95 to 1.05 pu of 400 V (a 5 % budget for the LV network inside the EN 50160 band of 0.90 to 1.10), transformer 100 %, every cable 100 % of its thermal rating. All can be changed per request (`v_min_pu`, `v_max_pu`, `trafo_max_pct`, `line_max_pct`). Each result gives the hours over each limit (`hours_over_limit`), i.e. the hours that need flexibility. |

### The grid: published feeder, sized for Austin homes
The published test case is a UK feeder sized for UK homes. Austin homes peak at about twice that load (air conditioning,
about 3.2 kW per home at the substation peak). With the published cables, the cable at the substation is already over
its rating on the peak day of 2018, and the voltage falls below 0.95 pu, with no new EVs. `cim/make_lv_zip.py` therefore
sizes the feeder the way a DSO would for these homes, **with no headroom left**: the network is at the edge of its
capacity today, so added EVs push it over the limits and flexibility is needed.

| | Published | Used (defaults) |
|---|---|---|
| Transformer | 800 kVA, the whole substation, for this one feeder | 200 kVA: the feeder's share (an 800 kVA substation supplies several feeders); IEC R10 size; same per-unit impedance (uk 4 %) |
| Main cable (58 sections) | 0.249 ohm/km (Al 120 mm2), rating 272 A | one size up, Al 185 mm2, 0.164 ohm/km, 340 A |
| Branch cables (75 sections) | 0.772 ohm/km (Cu 25 / Al 35-50 mm2) | unchanged, 145 A |

The CIM file has no current limits. The ratings are the HD 603 S1 values for XLPE cables in earth (20 C, 3 loaded
conductors). The published version is still available with `--trafo-kva 800 --main-r-ohm-km 0.249`, together with the
env vars `TRAFO_KVA=800 MAIN_CABLE_A=272`.

On the Austin data, the peak day (27 Aug 2018) with today's EVs is expected at about 98 % of the transformer and 84 % of the
main cable. Doubling the EV homes takes the transformer over 100 % in the evening hours.

Limitations:
- The model is balanced (positive sequence), while the homes are single-phase. Real per-phase voltages are lower and
  phase currents are higher.
- The data is hourly, so the short charger peaks inside an hour are averaged out.
- Both effects make the results optimistic: the real network breaks earlier.

How the scenarios are built (`service/scenarios.py`):
- **Added EVs**: a home that gets an EV draws a real charging day of an Austin EV home from the 3 weeks around the
  studied day (same weekday or weekend type), so the charging keeps the observed timing and diversity.
- **Added PV**: a home that gets PV gets the median system size times that day's PV shape.
- **Removed EVs**: when a scenario has fewer EVs than the data, the car circuit is subtracted.
- **Seeded order**: the order in which homes get EVs or PV is seeded, so the scenarios are nested (20 EVs includes
  the homes of 10 EVs).
- **Reactive power**: pf 0.95 for consumption.

```
POST /scenarios        {"days": ["peak"], "scenarios": [{"name": "ev20", "n_ev": 20}], "v_min_pu": 0.95}
                       every field is optional; {} runs the defaults (about 20 power flows, about 2 min)
GET  /scenarios/{id}   status, per day and scenario: V min / V max, transformer %, violations, hosting capacity
GET  /site             the homes, the EV / PV homes in the data, the chosen days, which unit sits on which load point
```
Results go to InfluxDB (database `openaiflex`):
- `lv_scenario,site,day_type,scenario` with `vmin_pu, vmax_pu, trafo_loading_pct, max_line_loading_pct,
  max_line_current_a, net_load_kw`.
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

**1. The LV feeder in TWIN-REV.** TWIN-REV takes the single `cel3_*.zip` in `dpsim_assets` as cell 3. Give every
changed grid a new archive name, because TWIN-REV's DPsim service keeps the XMLs of a name it has already seen.
```bash
git clone https://github.com/dpsim-simulator/cim-grid-data ~/cim-grid-data
cd ~/substation-flexibility/twinrev
python3 cim/make_lv_zip.py ~/cim-grid-data/IEEE_EU_LV/IEEE_EU_LV_reduced cel3_lv200.zip
A=~/TwinRev/digital_twin_backend/fast_api/apisrc/dpsim_assets
rm -f $A/cel3_*.zip && cp cel3_lv200.zip $A/          # only one cel3_* archive
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

**5. Network view (the digital twin on a diagram).** Open http://localhost:8002/view (with the port-forward of
step 3). It shows the single-line diagram of the feeder (positions from the CIM diagram layout), and for every hour:
- cables coloured by loading (green < 90 %, amber 90-100 %, red over rating);
- node voltages, coloured red when outside the limits;
- homes drawn by their net load (blue = exporting PV);
- the transformer.

Choose the day (peak, PV or any date of 2018) and the scenario (today, 2x EV, EV in every home, 2x PV, or your own
numbers), then press Run: one power flow in TWIN-REV, about 5-10 s. The strip of 24 hours shows which hours hold
(green), are close (amber) or break (red); click an hour or press play. Behind it: `POST /grid` (state of every node,
cable and the transformer per hour) and `GET /grid/layout`.

## Tests
```bash
cd twinrev && python3 -m pytest -q tests      # scenario construction on synthetic data (no DPsim needed)
```
The full chain was tested on synthetic data:
- DPsim 1.4 with TWIN-REV's DSO router and its dpsv service, the sized feeder, 55 units, 21 power flows.
- DPsim on this feeder matches the NEPLAN load flow in the same CIM export within 0.002 V at all 135 nodes.

## Files
- `service/app.py`: API, scenarios, hosting capacity, InfluxDB output.
- `service/scenarios.py`: Austin data and scenario construction.
- `service/grid.py`: profiles into TWIN-REV, pipeline call, voltages and transformer loading.
- `cim/make_lv_zip.py`: IEEE EU LV CIM to TWIN-REV cell-3 archive. Loads are renamed `lod_01..55`, because dpsv
  matches profiles by name prefix. Transformer share and main cable size are options.
- `service/lv_lines.json`: cable class of each line, from the CIM (`--lines-json`), for the thermal ratings.
- `service/lv_layout.json`, `cim/make_layout.py`: the diagram of the feeder (from the CIM diagram layout).
- `service/view.html`: the network view (`GET /view`).
- `tests/`: synthetic data generator and unit tests.
