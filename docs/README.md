# Documentation

OpenAIFlex Task 1.1 (ICCS/NTUA): microservices for the SOGNO-based AI-ADMS.

| Document | What it covers |
|---|---|
| [architecture.md](architecture.md) | The microservices, how they sit in SOGNO, data flow, interfaces, what is done and what is not |
| [flexibility-service.md](flexibility-service.md) | Substation flexibility: day-ahead forecast and kW down / up from smart-meter data and weather only |
| [digital-twin-service.md](digital-twin-service.md) | What-if EV / PV scenarios on a digital twin of an LV substation (TWIN-REV + DPsim), network view |
| [setup.md](setup.md) | Full local install: WSL2, k3s, SOGNO stack, TWIN-REV, both services, Grafana, troubleshooting |

Method details and test results of the flexibility method: [`../flexibility/README.md`](../flexibility/README.md),
[`../flexibility/experiments/RESULTS.md`](../flexibility/experiments/RESULTS.md),
[`../flexibility/docs/experiment_log.md`](../flexibility/docs/experiment_log.md).
Grid assumptions of the twin: [`../twinrev/README.md`](../twinrev/README.md).
