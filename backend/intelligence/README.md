# Waypoint intelligence

The original `Waypoint-Datathon` directory is not imported at runtime and may be moved away.
This directory contains offline training, evaluation, export and allocation tools.
`backend/services/intelligence` is the independently deployable inference API. It preserves the supplied feature engineering, training/inference, forecast, integer-scaled
allocation validator and CP-SAT policy code. Adaptations redirect experiment output to a private
workspace, add a compact reproducible Task 1 candidate and expose saved-model inference through
`services/intelligence`. The original task modules retain the full experiment routines; invoke them only deliberately.
The recommended compact runtime training/export commands below avoid that full grid.

## Private workspace

The authorized CSVs, copied forecast artifact, generated Task 1 artifacts and exports are already
in `backend/private/intelligence/` on this machine. That directory is gitignored and excluded from
Docker builds; Compose mounts it read-only into inference/operations. Back it up separately
before moving this checkout. A fresh clone needs the authorized data and models restored.
Never upload arbitrary pickle/joblib files: they execute code when loaded. Only administrator
provisioned artifacts with the private SHA-256 manifest are loaded; this is integrity checking,
not a substitute for trusting the artifact producer.

To reproduce the import from an authorized source elsewhere:

```sh
python backend/intelligence/import_workspace.py /path/to/authorized/datathon
```

It refuses to overwrite differing files. The existing import manifest records source hashes.
No notebooks, caches, the original Git repository or 391 MB of experiment checkpoints are required.

## Train and export

From the repository root, use Python 3.13 and the backend development environment documented in
`backend/README.md` (the scientific versions are pinned to the saved artifact's sklearn 1.9.1):

```sh
export PYTHONPATH="$PYTHONPATH:$PWD/backend/intelligence:$PWD/backend/services/intelligence/src:$PWD/backend/packages/contracts"
python backend/intelligence/train_runtime.py
python backend/intelligence/export_runtime.py --optimize --seconds 20
python backend/intelligence/validate_submissions.py
python backend/intelligence/write_policy.py
```

Task 1 fits strictly before 2026-01-05 and evaluates 5,035 later rows without refitting on holdout.
The supplied workspace did not contain its claimed final Task 1 artifacts. The new compact linear
candidate scored service RMSE 6.948 minutes / MAE 4.316; late log loss 0.1542, Brier 0.0461,
ROC AUC 0.9658 and PR AUC 0.8277. These are this candidate's measurements, not a reproduction
of the source README's missing boosted-model results. Models are written locally; training is
never triggered by an API request. Restart inference after replacing verified artifacts.

Task 2A uses the supplied saved Ridge ensemble. It counts deferred/not-run demand, combines
training and Task 1 test order records, and uses requested order weeks. The 10-week holdout
aggregate total/chilled WAPE reproduced as 3.9641%; macro subgroup WAPE from the original
report is a different aggregation. The UI's method identifies the model and historical horizon.
These are forecasts for the supplied horizon, not continuously refreshed forecasts for today's date.

Task 2B preserves whole `order_ref` decisions, available home-depot vehicles, reefer/van access,
exact volume/weight, two trips overall, same brand/district per trip, per-order handling and
separate 270-minute Fresh / 480-minute Style+Tech budgets. The bounded optimizer records
feasible incumbents and objective bounds; timeouts do not prove global optimality. Generated
exports and detailed feasibility/optimization reports stay under `backend/private/intelligence`.
No monetary shortfall costs are invented.

## Service and UI

The separate CPU inference container exposes authenticated dispatcher/admin endpoints:

- `POST /api/v1/intelligence/predictions` — up to 500 known test delivery IDs.
- `POST /api/v1/intelligence/planned-predictions` — a complete planned route batch, planned inputs only.
- `GET /api/v1/intelligence/forecast` — saved 60-row template forecast (depot scoped for assigned dispatchers).
- `GET /api/v1/analytics/plan-predictions?plan_id=...` — operations constructs planned-only inputs from persisted plans.

The Dispatcher allocation screen can request handling/late-risk estimates; its Analytics screen uses
learned demand forecasts. Estimates do not replace hard planning/publication checks. Models and
scientific libraries stay outside operations. Operations uses bounded HTTP calls and safe 503
responses on inference failure. No labels, POD outcomes or actual arrival times enter live inputs.
Send complete routes together because prefix-load and route-size features need route context.

Live reference tables must cover the plan date. The supplied calendar/road data has a finite
historical range; unsupported dates are rejected instead of inventing weather, holidays or road
conditions. Update authorized reference data and evaluate drift before enabling later production
dates. Synthetic/geocoded district positions are approximate, not authoritative road directions.

The source final notebook is `Waypoint_FinalNotebook.ipynb`. Execute it in the pinned
Datathon environment (`requirements.lock.txt`); retain data-bearing executed copies privately.
The local walkthrough freezes demo time at 09:00; production must set `DEMO_MODE=false`.

## Workspace configuration

`WAYPOINT_INTELLIGENCE_WORKSPACE` selects an alternative private workspace. The default is
`backend/private/intelligence`. The older `WAYPOINT_DATATHON_WORKSPACE` variable and
`backend/private/datathon` directory remain fallback inputs for existing deployments; the new
variable takes precedence. Data, models and exports remain excluded from Git and Docker images.

Bare `pytest -c backend/pytest.ini` includes the intelligence runtime and modelling tests as
well as the application suites. Production deployment and human competition deliverables
remain subject to the acceptance boundaries in the [challenge verification](../../docs/challenge-verification.md).

## Implemented capabilities

| Capability | Entry point |
|---|---|
| Feature preparation and chronological training/evaluation | `features.py`, `train_runtime.py`, original task modules |
| Handling-time and late-arrival predictions | Separate service's known-ID and planned-route endpoints; Dispatcher planning panel |
| Ten-week demand forecast and measured backtest | Separate forecast endpoint; Operations analytics and Dispatcher Analytics screen |
| Whole-order peak-day allocation and exact feasibility checks | `task2b.py`, `export_runtime.py --optimize` |
| Template-aligned prediction/allocation exports and fresh-process verification | `export_runtime.py`, `validate_submissions.py` |
| Prioritization policy and per-trip calculations | `write_policy.py` |
| Reproducible saved-model inference notebook | `Waypoint_FinalNotebook.ipynb` |
| Identity, depot scope, input validation and model integrity | Inference service contracts and security tests |

These capabilities use the copied backend-owned assets. The original `Waypoint-Datathon`
folder is an optional import source only; it is not part of runtime configuration.
