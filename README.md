# LeakLogic AI 4.3 — India-first RAG edition

This beginner project adapts the ECE Scholar Tutor workflow: local Hugging Face embeddings, persistent retrieval, authorized PDF ingestion, optional configurable OpenRouter LLM, and Streamlit. **No FAISS or external vector database.** SQLite stores chunk text and embedding arrays; Python cosine similarity ranks them. This is suitable for a small document library, not millions of sensor rows. Hydraulic data remains separate from document retrieval. The LLM cannot decide or change leak diagnoses.

## Windows setup (Python 3.12)
1. Extract the ZIP and open `LeakLogic_AI_4_2_RAG` in VS Code. Open PowerShell in that folder.
2. Run these commands in order:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe ingest.py
```

Do not overwrite an existing .env. Open your local `.env` and enter a NEW OpenRouter API key if using cloud LLM answers. Never share or commit that key. `openrouter/free` is the configurable default model route, subject to provider availability and limits. No key is needed for local document retrieval, indexing or hydraulic calculations. The initial embedding model download needs internet, and package/model downloads can require multiple GB of storage. An optional `setup.ps1` performs equivalent installation without overwriting an existing `.env`.

3. Backend terminal:
```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```
4. Open a second terminal in the same folder:
```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```
Open http://127.0.0.1:8501. API docs: http://127.0.0.1:8000/docs.

## Indian data
The included original-publication transcription has 25 Nagpur hourly rows and a SQLite DB; no verified leak labels. The IIT Bombay WaterGEMS and Delhi/Bengaluru archives are NOT included. Retrieve them directly with:
```powershell
.\.venv\Scripts\python.exe download_originals.py
```
Consult `sources.csv` and `datasets/DATA_GUIDE.md` for manual links, licensing and limitations. The guide's paths are relative to this project root. Downloaded archives require inspection/extraction and source-specific mapping before use; no automatic raw hydraulic importer is claimed. International LeakDB is deliberately excluded. Hugging Face supplies the embedding model, not Indian field data. No synthetic measurement dataset is bundled. Unit tests use synthetic fixtures only.

## Document ingestion and RAG
Place authorized searchable PDFs in `documents/` and rerun `ingest.py`, or upload in the Document library. Bundled blueprints and Nagpur data/source notes are indexed by default. Scanned pages are skipped. CSV row citations preserve original evidence type. No cloud service is used for indexing. Local search is available without an LLM. The LLM receives only the current question and retrieved excerpts after consent; answers may still be wrong and need source review. Model weights are not bundled; the embedding model downloads on first use; LLM inference uses OpenRouter. The application does not train a model or include full local generative LLM weights. This app is localhost-only and has no production authentication.

## Hydraulic backend and evaluation
`physics.py` implements Bernoulli head, continuity residual, Darcy friction and ideal orifice flow helpers. Cross-cycle fitting compares zero residual, offset, scale bias and pressure power-law leak models with weighted BIC; pressure is a midpoint proxy. The current diagnostic path uses continuity and power-law fitting, not a full network hydraulic solver. Supply stable verified window summaries in `templates/stable_cycle_readings.csv` (one per branch/cycle). Geometry, pressure uncertainty, whole-cycle volume fallback and adaptive information-per-cost test scheduling from v4.2 are not fully implemented; planner suggests tests, never invents their outcomes. Agents are rule-based, LangGraph routes them, and a LangChain structured tool calculates residuals. No control of physical equipment.

`evaluate.py` scores independently verified held-out leak/normal cases with predictions, tracks unresolved cases and coverage. It cannot validate label provenance automatically. No valid Indian labelled branch dataset was available. Actual accuracy, localization accuracy and win rate are **unknown**; no accuracy claim or patentability claim is made. Test against real labels only after independent validation; the current prototype is not a completed scientific backtest engine.

## Main files
- `app.py`: Streamlit UI; `main.py`: FastAPI; `agents.py`: four agents.
- `library.py`, `ingest.py`, `llm.py`: local RAG and optional LLM.
- `physics.py`, `models.py`, `evaluate.py`: deterministic analysis and evaluation.
- `datasets/`, `templates/`, `documents/`: Indian sources, input schemas, project documents.

## Tests
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
Core unit tests use a fake embedder, not actual model downloads. End-to-end LangGraph, Streamlit and external provider access must be verified on your laptop. See the included project blueprint and review for further development requirements.

## Primary feature: possible leakage screening (v4.3)
The first workspace, **Leakage detection**, accepts paired inlet/outlet flow readings for a named pipeline segment and supply cycle. It computes:

- `R = Q_in - Q_out - accounted_storage_change - known_branch_taps`
- `sigma_R = sqrt(sigma_in^2 + sigma_out^2)` assuming independent meter standard uncertainties
- A per-window possible-leak signal when `R > 3 * sigma_R`, but only when the user marks the window as stable and full-pipe.
- A branch-level **POSSIBLE LEAK** status when the threshold is exceeded in at least two distinct verified cycles. A single flagged cycle is reported as an anomaly needing recheck.

This is a transparent rule-based screening baseline. It does not prove a leak, calculate an exact leak position, estimate a calibrated probability, or establish field accuracy. Unmetered outlets, storage changes, pump transitions, meter bias, air and incorrect segment boundaries can mimic leakage. The sample CSV rows are illustrative examples, not real Indian sensor observations. Replace them with measured data before interpreting results.

The four-agent LangGraph diagnostic path remains available under **Hydraulic diagnosis** for cross-cycle investigation and recommended follow-up checks. The new first-page detector provides the direct possible-leak screening workflow; the RAG assistant remains a supporting research feature and the LLM does not decide the leak status.

### New endpoint
`POST http://127.0.0.1:8000/detect` with JSON `{ "rows": [ ... ] }`. The Streamlit Leakage detection page calls this endpoint and displays per-cycle evidence, per-branch status and a downloadable JSON report.

### CSV fields for leakage screening
`branch_id, cycle_id, q_up_l_s, q_down_l_s, pipe_storage_change_l_s, branch_tap_l_s, meter_up_sigma_l_s, meter_down_sigma_l_s, full_pipe_flag, stable_window_verified`

All flow fields and meter uncertainties are in L/s. Meter uncertainties must be positive standard uncertainties. `pipe_storage_change_l_s` and `branch_tap_l_s` must be measured/known estimates, not guessed values. The stable/full-pipe flags must be verified by the operator.

### Updated tests
The test suite now includes repeated-imbalance detection, no-flag behaviour below threshold and rejection of unverified windows. Run the tests using the command in the Tests section.

## LeakLogic AI 4.6 — whole-pipeline spatial screening

The **Whole-pipeline mapping** workspace accepts synchronized readings from monitoring stations along a pipeline. It evaluates every adjacent-station interval, stores chainage as integer millimetres, flags repeated unexplained flow loss, and records reports in `incidents.db`.

### Spatial CSV columns

`pipe_id, cycle_id, timestamp, station_id, distance_m, flow_l_s, meter_sigma_l_s, known_withdrawal_l_s, full_pipe_flag, stable_window_verified`

- `distance_m` is the station's chainage from the start of the pipe.
- Supply at least two stations per pipe, cycle and timestamp.
- Provide readings at matching timestamps; use repeated independent cycles for escalation.
- `known_withdrawal_l_s` is the known withdrawal between the upstream and downstream stations for that interval (enter it on the downstream station row).
- Verify full-pipe and stable-window flags before relying on the screening result.

### Critical resolution limitation

A 200 km pipe contains 200,000,000,000 one-millimetre coordinate positions. The application uses sparse station/interval records and integer millimetre chainage; it does **not** create 200 billion rows or claim that every millimetre is physically sensed. With this flow-balance method, an anomaly is bracketed between adjacent monitoring stations. Actual localization resolution is therefore limited by station spacing, meter uncertainty, synchronization and hydraulic conditions. Add intermediate stations or use a validated distributed acoustic/fibre-optic or transient-sensing system to improve localization. A millimetre coordinate format is not millimetre detection accuracy.

The spatial screen is a possible-leak indicator, not leak confirmation. Unmetered demand, storage changes, bypasses, pump operations, air and sensor bias can mimic leakage. Confirm findings in the field. It cannot calculate measured accuracy without independent leak/normal ground-truth labels.

### API

`POST /spatial-detect` with JSON `{ "rows": [...], "pipe_length_m": 200000 }` analyzes and stores a spatial report in `incidents.db`.

Run tests with `python -m unittest discover -s tests -v`.

The bundled `templates/spatial_pipeline_readings.csv` contains **illustrative test values only** to demonstrate file format and a repeated flow imbalance. It is not an Indian field dataset and must be replaced with calibrated, synchronized measurements before real analysis.

## LeakLogic AI 4.6 — HMWSSB government-data request pack
The `government_data_access/` folder adds an academic request letter, official source register, empty CSV schemas and a workflow for obtaining authorized HMWSSB records. **No HMWSSB government SCADA data is bundled** because access has not been granted and no public raw sensor archive has been verified. Existing Nagpur research observations remain distinct from government-provided records. See `government_data_access/README.md` before claiming any data is official or field-validated.

## LeakLogic AI 4.6 — BattLeDIM benchmark importer
The **BattLeDIM benchmark** workspace accepts the publisher's original wide-format CSV files for pressure, flow and leakage-reference time series. It converts sensor columns into a normalized long CSV while preserving year, type, timestamp, sensor ID, value and source filename. Optional 2018 historical data and 2019 evaluation data can be compared using a simple per-sensor median/standard-deviation screen (absolute z-score ≥ 3).

**Source and interpretation:** BattLeDIM's official documentation describes 5-minute SCADA samples, 33 pressure sensors (metres of head), 3 flow sensors (m³/h), a tank-level sensor (m), and 82 AMR demand devices (L/h). The 2018/2019 benchmark files and network configuration are for L-Town; the dataset configuration includes generated leakage scenarios. Treat this as an international benchmark, not Indian government field data. Keep the leakage-reference series separate from pressure/flow measurements. A statistical anomaly is not a confirmed leak and this simple baseline is not a competition-scoring implementation. See the original source and units before interpretation:
- https://zenodo.org/records/4017659
- https://battledim.ucy.ac.cy/?page_id=33

Recommended files: `2018_SCADA_Pressures.csv`, `2018_SCADA_Flows.csv`, `2019_SCADA_Pressures.csv`, `2019_SCADA_Flows.csv`; optional `2018_Leakages.csv` and `2019_Leakages.csv`. The full Zenodo archive is approximately 550 MB; download only the required CSVs. The organizer page may ask for contact details, while the Zenodo record lists the individual files. Do not upload `2019_Leakages.csv` as SCADA pressure or flow. The importer does not invent station chainage or transform L-Town sensors into a straight pipeline.

Test the importer with `python -m unittest tests.test_battledim_importer -v` or run the full suite with `python -m unittest discover -s tests -v`.


### BattLeDIM CSV format compatibility (v4.6.1)
The importer supports the official semicolon-delimited BattLeDIM SCADA export format, including decimal-comma values (for example `Timestamp;n1;n4` and `28,92;33,87`), as well as ordinary comma-delimited CSV files. Sensor identifiers are preserved as supplied. Imported sensor time series are not automatically converted into geographic chainage or serial pipeline stations.


## LeakLogic AI 4.8 — Pipeline diagnostic card

After uploading a valid paired-flow CSV in **Leakage detection** and selecting **Analyze for possible leakage**, the app now displays a diagnostic card for a selected measurement:
- inlet and outlet flow (L/s)
- gross inlet/outlet flow difference (L/s)
- indicative gross imbalance volume over a user-selected duration
- branch-level possible-leak/anomaly/no-signal status
- residual after entered storage and known-tap adjustments, meter uncertainty, z-score and eligibility evidence

The potential-loss figure is the gross inlet-minus-outlet difference multiplied by the selected duration. It is an estimate **if that difference were sustained**, not a confirmed leak volume. The detector's status continues to use adjusted residual, meter uncertainty, stable/full-pipe verification and repeated distinct cycles. A BattLeDIM wide-format SCADA file is not a substitute for the paired-flow CSV schema and must not be sent to the spatial endpoint.
