# OpenAIFlex: ICCS microservices (Task 1.1)

Microservices for the OpenAIFlex SOGNO stack (k3s + RabbitMQ + InfluxDB + Grafana). Each folder is one microservice
with its own code, Dockerfile, Kubernetes manifest, Grafana dashboard and tests.

| Folder | Microservice | Data | Status |
|---|---|---|---|
| [`flexibility/`](flexibility/README.md) | Substation flexibility: day-ahead load forecast and kW up / down per hour, from smart-meter data and weather only (`flexsub`) | REFIT, Plegma, LCL, UK-DALE (public); Pecan Street (local only) | running on the stack ([service](flexibility/service/README.md)) |
| [`twinrev/`](twinrev/README.md) | Scenarios on a digital twin (TWIN-REV + DPsim): what-if EV / PV adoption on an LV substation, voltages, transformer loading, hosting capacity | IEEE European LV feeder (public CIM) + Pecan Street Austin homes (local only) | running on the stack |
| FL | Federated learning | | planned |
| AI agents | | | planned |

Licensed household data (Pecan Street Dataport) is never committed and never baked into an image. It stays in
git-ignored folders on the machine and is mounted at run time.

Tests:
```bash
cd flexibility && python3 -m pytest -q tests
cd twinrev && python3 -m pytest -q tests
```
