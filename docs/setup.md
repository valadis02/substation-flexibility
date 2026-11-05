# Local setup: SOGNO stack, TWIN-REV and both microservices

Every command was run on Windows 11 + WSL2 (Ubuntu 22.04) in October 2026. Native Ubuntu 22.04 works the same;
skip Part 0.

Result at the end:
- k3s with namespace `sogno` running RabbitMQ (databus, MQTT on), InfluxDB 1.x and Grafana (the SOGNO single-node
  infrastructure);
- the **flexibility service** (`flexibility/`), with REFIT development data and a Grafana dashboard;
- **TWIN-REV** in namespace `digital-twin` (smoke test 9 / 9);
- the **digital-twin scenario service** (`twinrev/`), with the network view at `/view` and a Grafana dashboard.

| Part | What |
|---|---|
| 0-5 | WSL2, k3s, Helm, RabbitMQ, InfluxDB, Grafana |
| 6 | flexibility service |
| 7 | TWIN-REV |
| 8-9 | digital-twin scenario service |

Rule of thumb: the prompt `PS C:\...>` is PowerShell, the prompt `user@host:~$` is Ubuntu. Every command below runs
in Ubuntu unless it says PowerShell. If you have several WSL distributions, always open this one with
`wsl -d Ubuntu-22.04`.

## Where we deviated from the official SOGNO docs (and why)

Official docs: https://sogno.energy/docs/getting-started/single-node/ and
https://github.com/sogno-platform/example-deployments

| Official instruction | Problem today | What we did |
|---|---|---|
| RabbitMQ from `bitnami/rabbitmq` Helm chart | Bitnami no longer publishes free images; pods end in `ImagePullBackOff` | plain Deployment with the official `rabbitmq:3.13-management` image, MQTT plugin enabled at start (Part 3) |
| Grafana from `stable/grafana` | the `stable` Helm repo no longer exists | official `grafana/grafana` chart (prints "This chart is deprecated" but works), with persistence on |
| Tested on Ubuntu 20.04 (native) | WSL2 has no systemd by default; k3s installer needs it | WSL2 Ubuntu 22.04 with `systemd=true` in `/etc/wsl.conf` |
| PMU demo feeds InfluxDB via Telegraf from MQTT topics in a SOGNO PMU JSON format | we have smart-meter data, not PMU data | our service reads/writes InfluxDB directly; RabbitMQ is installed but not used by the service yet |
| pyvolt/DPsim demo needs HugePages | not needed for our services | skipped |
| README path `ts-database/influxdb-helm-values.yaml` | folder is actually `database/` | irrelevant here, we write our own values file |

---

## Part 0: WSL2 + Ubuntu (Windows only)

PowerShell **as Administrator**:
```powershell
wsl --install -d Ubuntu-22.04
```
Create the Linux user when asked. Then **inside Ubuntu**:
```bash
sudo tee /etc/wsl.conf > /dev/null <<'EOF'
[boot]
systemd=true
EOF
```
Back in **PowerShell**:
```powershell
wsl --shutdown
wsl -d Ubuntu-22.04
```
Inside Ubuntu, check:
```bash
cd ~
ps -p 1 -o comm=          # must print: systemd
```

Rule of thumb: prompt `PS C:\...>` = PowerShell, prompt `user@host:~$` = Ubuntu. Everything below runs in Ubuntu.
Windows drives are under `/mnt/c/...`; Windows sees Ubuntu files at `\\wsl$\Ubuntu-22.04\home\<user>\...`.

## Part 1: k3s + Helm

```bash
sudo apt update && sudo apt install -y curl git python3-pip unzip docker.io
curl -sfL https://get.k3s.io | sh -
sudo k3s kubectl get node                     # wait ~30 s until STATUS = Ready

curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
sudo chown -R $USER /etc/rancher/k3s/
echo 'export KUBECONFIG=/etc/rancher/k3s/k3s.yaml' >> ~/.bashrc
source ~/.bashrc
kubectl get node
helm version

helm repo add sogno https://sogno-platform.github.io/helm-charts
helm repo add influxdata https://influxdata.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
kubectl create namespace sogno
```
`docker.io` is installed here only to build our service image (Part 6). Docker Desktop on Windows is not needed.

## Part 2: RabbitMQ (databus, MQTT on)

```bash
mkdir -p ~/sogno && cd ~/sogno
cat > rabbitmq.yaml <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata: { name: rabbitmq, namespace: sogno }
spec:
  replicas: 1
  selector: { matchLabels: { app: rabbitmq } }
  template:
    metadata: { labels: { app: rabbitmq } }
    spec:
      containers:
      - name: rabbitmq
        image: rabbitmq:3.13-management
        command: ["sh","-c","rabbitmq-plugins enable --offline rabbitmq_mqtt && exec rabbitmq-server"]
        env:
        - { name: RABBITMQ_DEFAULT_USER, value: admin }
        - { name: RABBITMQ_DEFAULT_PASS, value: admin }
        ports:
        - containerPort: 5672
        - containerPort: 1883
        - containerPort: 15672
---
apiVersion: v1
kind: Service
metadata: { name: rabbitmq, namespace: sogno }
spec:
  selector: { app: rabbitmq }
  ports:
  - { name: amqp, port: 5672 }
  - { name: mqtt, port: 1883 }
  - { name: mgmt, port: 15672 }
EOF
kubectl apply -f rabbitmq.yaml
```

## Part 3: InfluxDB 1.x

```bash
cat > influx-values.yaml <<'EOF'
persistence:
  enabled: true
  size: 5Gi
EOF
helm install influxdb influxdata/influxdb -n sogno -f influx-values.yaml
```

## Part 4: Grafana (with persistence, so dashboards survive restarts)

```bash
helm install grafana grafana/grafana -n sogno \
  --set adminPassword=admin --set persistence.enabled=true --set persistence.size=2Gi
```
If you later change the admin password in the Grafana UI, use the new one in any future `helm upgrade`
(`--set adminPassword=...`), otherwise the secret and the real password disagree.

Check and create the database:
```bash
kubectl get pods -n sogno -w        # wait until rabbitmq, influxdb-0, grafana are 1/1 Running; then Ctrl+C
kubectl get pvc -n sogno            # grafana and influxdb-data-influxdb-0 must be Bound
kubectl exec -n sogno influxdb-0 -- influx -execute 'CREATE DATABASE openaiflex'
kubectl exec -n sogno influxdb-0 -- influx -execute 'SHOW DATABASES'
```

## Part 5: open the UIs

Port-forwards must stay running. Simplest: one Ubuntu window left open with
```bash
pkill -f port-forward; sleep 1
kubectl port-forward -n sogno svc/grafana 3000:80 &
kubectl port-forward -n sogno svc/rabbitmq 15672:15672 &
wait
```
- Grafana: http://localhost:3000 (admin / admin)
- RabbitMQ: http://localhost:15672 (admin / admin)

Grafana data source (once): Connections -> Data sources -> Add -> **InfluxDB**
- Query language: InfluxQL
- URL: `http://influxdb.sogno:8086`
- Database: `openaiflex`
- Save & test (green). Add it only once: repeated clicks create `influxdb-1`, `-2`, ... (delete those).

## Part 6: the flexibility service (`flexibility/`)

```bash
cd ~
git clone https://github.com/valadis02/substation-flexibility.git
cd ~/substation-flexibility/flexibility
sudo docker build -f service/Dockerfile -t openaiflex/flex-envelope:0.1 .
sudo docker save openaiflex/flex-envelope:0.1 | sudo k3s ctr images import -
kubectl apply -f service/k8s.yaml
kubectl rollout status deployment/flex-envelope -n sogno
```
- The first build downloads Python packages (3-5 min). **Do not press Ctrl+C** before it prints
  `Successfully tagged ...`. An interrupted build leaves no image, and the pod then shows `ErrImageNeverPull`.
- `k8s.yaml` uses `imagePullPolicy: Never`, so the image comes from the local import, not from a registry.

Load the REFIT development data into InfluxDB. Held-out homes and locked-test periods are skipped automatically:
```bash
kubectl exec -n sogno deploy/flex-envelope -- python load_dataset.py refit --site refit --from 2014-08-15
```
Open the API:
```bash
kubectl port-forward -n sogno svc/flex-envelope 8001:8000 > /tmp/pf-flex.log 2>&1 &
```
Swagger is at http://localhost:8001/docs. Port 8001 is used because 8000 is often taken.
1. Run `POST /dayahead` with `{"site": "refit", "evaluate_with": "refit"}` and note the `id`.
2. After about a minute, `GET /dayahead/{id}` returns `"status": "done"` for target day 2015-01-26.

Grafana:
1. Go to Dashboards, then New, then Import, and upload `flexibility/service/grafana_dayahead.json`.
2. Choose the InfluxDB data source.

Expected result: the actual load is inside the 90 % band 22 / 24 h; kW down estimate / truth 0.97; kW up 1.20.

## Part 7: TWIN-REV (namespace `digital-twin`)
```bash
cd ~
git clone https://github.com/Crete-Valley/TwinRev.git
cd TwinRev
chmod +x scripts/*.sh
mkdir -p t4.3-optimization/project/data_outputs     # the optimizer image expects this folder
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
sudo ./scripts/build-images.sh
sudo ./scripts/k3s-import-images.sh
./scripts/create-secrets.sh
kubectl apply -k deploy/k8s
kubectl -n digital-twin get pods -w                  # wait until all pods are Running, then Ctrl+C
kubectl -n digital-twin create job --from=cronjob/simulated-data-fetch data-fetch-now
./scripts/smoke_test.sh                              # expect: Passed 9 / Failed 0
```
The forecasting CronJob needs an external API token from the TWIN-REV maintainers. Without it only that job fails;
nothing below needs it.

## Part 8: the digital-twin scenario service (`twinrev/`)

### 8a. The code
The repo is already cloned in Part 6. Also clone the public CIM grids:
```bash
cd ~ && git clone https://github.com/dpsim-simulator/cim-grid-data.git
```

### 8b. The grid into TWIN-REV (cell 3)
TWIN-REV takes the single `cel3_*.zip` in `dpsim_assets` as DSO cell 3. Give every changed grid a new archive name,
because TWIN-REV's DPsim service keeps the XMLs of any name it has already seen.
```bash
cd ~/substation-flexibility/twinrev
python3 cim/make_lv_zip.py ~/cim-grid-data/IEEE_EU_LV/IEEE_EU_LV_reduced cel3_lv200.zip
#   expect: renamed: 55 / rating 200 kVA / main cable class: 0.164 ohm/km
A=~/TwinRev/digital_twin_backend/fast_api/apisrc/dpsim_assets
rm -f $A/cel3_*.zip && cp cel3_lv200.zip $A/ && ls $A
cd ~/TwinRev
sudo docker build -t cvdt/dt-backend:local digital_twin_backend/fast_api
sudo docker save cvdt/dt-backend:local | sudo k3s ctr images import -
kubectl -n digital-twin rollout restart deployment/dt-backend
kubectl -n digital-twin rollout status deployment/dt-backend
```

### 8c. Household data (Pecan Street Austin, local only)
The data comes from Pecan Street Dataport: Austin, 15-minute data, 25 homes, 2018. You need your own Dataport
account. **The licence does not allow redistribution**: never commit the data, put it in an image, or send it on.
```bash
cd ~/substation-flexibility/flexibility
pip install -q -r requirements.txt
PYTHONPATH=. python3 scripts/prepare_data.py pecan_austin /mnt/c/Users/<you>/Downloads/15minute_data_austin.csv
ls data/processed/pecan_austin | head        # mains.csv.gz + appliances_P*.csv.gz
git status --short                           # must be empty: the data is git-ignored
```
**Without Dataport access**, skip this step and use the ready-made synthetic set in the repo:
`twinrev/data/synthetic_55`. It holds 55 invented homes (14 EV, 43 PV) tuned like the real feeder: today at the
limit, 2x EV over it for 3 evening hours, an EV in every home for 5. The view marks it as synthetic. Point the deployment at it in 8d (`DATA=`).

### 8d. Access to TWIN-REV's database, then deploy
TWIN-REV allows PostgreSQL only from its own namespace. The service's manifest adds a NetworkPolicy for it, and it
needs the DB URL as a secret in `sogno`:
```bash
PW=$(kubectl -n digital-twin get secret dt-secrets -o jsonpath='{.data.DB_POST_PASSWORD}' | base64 -d)
kubectl -n sogno create secret generic twinrev-db \
  --from-literal=TWINREV_DB_URL="postgresql+psycopg2://postgres:${PW}@postgres.digital-twin:5432/postgres"

cd ~/substation-flexibility/twinrev
sudo docker build -f service/Dockerfile -t openaiflex/twinrev-scenarios:0.4 .
sudo docker save openaiflex/twinrev-scenarios:0.4 | sudo k3s ctr images import -
DATA=$HOME/substation-flexibility/flexibility/data/processed/pecan_austin   # or $HOME/substation-flexibility/twinrev/data/synthetic_55
sed "s|__AUSTIN_DIR__|$DATA|" service/k8s.yaml | kubectl apply -f -
kubectl -n sogno rollout restart deployment/twinrev-scenarios
kubectl -n sogno rollout status deployment/twinrev-scenarios
```
The data folder is mounted read-only into the pod (hostPath), so no household data goes into the image.

## Part 9: use the twin
```bash
kubectl -n sogno port-forward svc/twinrev-scenarios 8002:8000 > /tmp/pf.log 2>&1 &
sleep 4; curl -s localhost:8002/health        # {"status":"ok"}
```
**Network view:** open http://localhost:8002/view in a browser.
- Choose the day (peak, PV or a date of 2018) and the scenario (Today, 2x EV, EV in every home, 2x PV, or your own
  numbers), then press **Run power flow**. This is one DPsim run in TWIN-REV, about 5-10 s.
- The 24 boxes show the hours that hold (green), are close (amber) or break (red). Click one, or press play.

**All default scenarios plus hosting capacity** (about 20 power flows, 2-3 min). The results also go to InfluxDB:
```bash
J=$(curl -s -X POST localhost:8002/scenarios -H 'Content-Type: application/json' -d '{}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])"); echo $J
while curl -s localhost:8002/scenarios/$J | grep -q '"status":"\(queued\|loading\|power\)'; do sleep 10; done
curl -s localhost:8002/scenarios/$J | python3 -m json.tool | head -80
```

**Grafana (optional).**
1. Open http://localhost:3000.
2. Go to Dashboards, then New, then Import, and upload `twinrev/service/grafana_scenarios.json`.
3. Choose the InfluxDB data source.
4. Set site = `austin`, day = `peak` or `pv`, and the time range 2030-01-01 to 2030-01-02 (the studied day is
   written on that date).

Swagger with every endpoint is at http://localhost:8002/docs.

## Troubleshooting (all seen during the first install)

| Symptom | Cause | Fix |
|---|---|---|
| `wsl: command not found` inside Ubuntu | `wsl` is a Windows command | run `wsl --shutdown` in PowerShell |
| `Expand-Archive` / `docker` not found in Ubuntu | PowerShell commands pasted into bash | use the bash commands above (`unzip`, `sudo docker`) |
| `cp: cannot stat .../Downloads/x` | browser saved elsewhere (OneDrive folder) or renamed `x (1).zip` | `find /mnt/c/Users/<you> -maxdepth 4 -name "x*"`; quote paths with spaces |
| pod `ErrImageNeverPull` | image not built / not imported (build interrupted) | rerun build + `docker save ... | k3s ctr images import -` + `rollout restart` |
| Swagger "Failed to fetch", Grafana page down | port-forward died (window closed, pod restarted) | rerun the port-forward; keep its window open |
| `bind: address already in use` on 8000/3000 | an old port-forward still holds the port | `pkill -f port-forward` and start again |
| port-forward started with `&` exits with `Exit 1` | started while the pod was restarting, or port in use | run it again (without `&` to see the error) |
| Grafana panel "No data" | time range is "Last 6 hours" | data are from 2014-2015; use the imported dashboard's range |
| odd values like `2014-08-1515`, `2GiGi` | double paste in the terminal | check the command before Enter |
| Grafana warns "Persistence is disabled" | installed without persistence | `helm upgrade grafana grafana/grafana -n sogno --set adminPassword=<pw> --set persistence.enabled=true --set persistence.size=2Gi` |
| `git commit`: "Author identity unknown" | git not configured in WSL | `git config --global user.name "..."` and `user.email "..."` |
| `git push` from WSL: "Password authentication is not supported", or `git-credential-manager.exe: Exec format error` | GitHub needs a token; the Windows credential helper does not run from this WSL | use a personal access token as the password, or commit in WSL and push from Windows: in PowerShell `git -c safe.directory=* pull --ff-only "\\wsl.localhost\Ubuntu-22.04\home\<user>\substation-flexibility" main`, then `git push` |
| `kubectl` times out to another IP (e.g. 192.168.x.x) | wrong WSL distribution open (`wsl` opens the default one) | `wsl -l -v`, then `wsl -d Ubuntu-22.04` |
| Bash commands fail in `PS C:\...>` (e.g. `&&`, `Z=$(...)`, `head`) | pasted into PowerShell | run them in Ubuntu; PowerShell only for Windows-side git |
| `/view` does not load, or shows an old version | port-forward dropped when the pod was replaced (`Exit 1`), or browser cache | `pkill -f "port-forward svc/twinrev-scenarios"`, start it again; private window or Ctrl+F5 |
| `TWIN-REV power flow failed` | dt-backend / dpsim-backend not running, or not exactly one `cel3_*.zip` | `kubectl -n digital-twin get pods`; `ls .../dpsim_assets` |
| new grid not used | DPsim keeps the XMLs of an archive name it has seen | give every changed grid a new archive name (e.g. `cel3_lv200.zip`) |
| `ModuleNotFoundError: flexsub` when running a script | script folder on the Python path, not the package | run from `flexibility/` with `PYTHONPATH=.` |


## After a reboot
```bash
wsl -d Ubuntu-22.04            # from PowerShell
kubectl get pods -n sogno      # k3s starts by itself; data and dashboards persist
kubectl get pods -n digital-twin
# then start the port-forwards (Parts 5, 6, 9)
```
