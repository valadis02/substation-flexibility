# Flexibility / day-ahead service (OpenAIFlex, SOGNO-style)

FastAPI job service over `flexsub`. Inputs and outputs live in InfluxDB 1.x (the SOGNO single-node stack:
k3s + RabbitMQ + InfluxDB + Grafana).

| Measurement | Tags | Fields | Written by |
|---|---|---|---|
| `meter` | site, home | kw (hourly) | `load_dataset.py` (or a real meter feed) |
| `weather` | site | temp, rh, cloud, rad, is_day | `load_dataset.py` (in operation: a weather forecast for the target day) |
| `dayahead` | site | forecast_kw, forecast_lo_kw, forecast_hi_kw, down_kw, up_kw, temp_c; with `evaluate_with`: true_down_kw, true_up_kw, realised_flexible_kw, actual_kw | `POST /dayahead` |
| `substation`, `envelope` | site | backtest outputs | `POST /envelope` |

Endpoints: `POST /dayahead` (one substation, next day: 90% forecast band + kW down / up per hour), `POST /envelope`
(backtest over a period), `GET /dayahead/{id}`, `GET /envelope/{id}`, `GET /health`. Swagger at `/docs`.

The day-ahead run uses meter data strictly before the target day (checked: multiplying the target-day load by 5 does
not change the output). `evaluate_with=<dataset>` compares with the dataset's sub-metering (research data only;
never used for the prediction). `load_dataset.py` loads development data only (held-out homes and locked-test
periods from `data/splits.json` are skipped).

## Deploy on the single-node stack (namespace `sogno`)
```bash
cd flexibility                                                                  # this microservice's folder
sudo docker build -f service/Dockerfile -t openaiflex/flex-envelope:0.1 .
sudo docker save openaiflex/flex-envelope:0.1 | sudo k3s ctr images import -
kubectl apply -f service/k8s.yaml
kubectl rollout status deployment/flex-envelope -n sogno
kubectl exec -n sogno deploy/flex-envelope -- python load_dataset.py refit --site refit --from 2014-08-15
kubectl port-forward -n sogno svc/flex-envelope 8000:8000        # http://localhost:8000/docs
```
`POST /dayahead` with `{"site": "refit", "evaluate_with": "refit"}` -> target day 2015-01-26 (last complete
development day). Grafana dashboard: `service/grafana_dayahead.json`.

`fake_influx.py` is an in-memory stand-in for local tests without InfluxDB.
