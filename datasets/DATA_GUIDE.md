# LeakLogic AI 4.2 | Indian dataset starter pack

This ZIP is a dataset acquisition package, not the application source code.

## Included now
- Nagpur Ramnagar: 25 published hourly observations (24 hours plus the closing midnight row), transcribed from Table 1 of Jadhao and Gupta (2018). Original reported values and unit-normalized CSVs are separate.
- `datasets/india_water.db`: SQLite database populated with those 25 observations, with unknown leak labels stored as NULL.
- Empty CSV schemas for future paired branch readings, pipe geometry, supply cycles and confirmed leak events. These are templates, not observations.
- Download script and sources manifest for the two original open archives.

## Download the original archives on Windows
Extract this ZIP. Open the extracted `LeakLogic_India_Datasets` directory in VS Code, open PowerShell, and run:

    py -3.12 download_originals.py

The script needs internet access and roughly 150 MB or more of free disk space (additional space to extract archives). No pip packages or API keys are needed. Publisher API availability may change; the script is syntax-checked, not end-to-end tested because outbound downloads were blocked in the authoring environment.

If the command fails, use the original publisher download buttons:
1. IIT Bombay WaterGEMS models, version 3: https://zenodo.org/records/7162154 — 794.6 kB RAR. Put in `datasets/iit_bombay/`. This is a hydraulic model archive, not a set of measured leak events. Check publisher terms before redistributing. The archive may require WaterGEMS or author-provided CSV exports for inspection; the Python application does not require WaterGEMS at runtime.
2. Delhi and Bengaluru supply schedules, version 1: https://doi.org/10.5683/SP3/QA0YQM — select Access Dataset / Original Format ZIP (101 MB). Save in `datasets/delhi_bengaluru/`. The archive contains published schedule data and research materials, not paired pressure/flow measurements or leak labels. Review the CC BY-NC 4.0 terms before commercial use. Preserve the publisher metadata and directory layout.

## Further Indian data access
- Hyderabad HMWSSB: https://data.opencity.in/dataset/?organization=hyderabad-metropolitan-water-supply-and-sewerage-board-hmwssb — public administrative data, not a verified branch-level sensor dataset. Contact the utility via your college for historical flow, pressure and repair records.
- CSIR-CEERI Pilani: https://github.com/neelabhsinha/Leakage-Detection-in-Smart-Water-Distribution-Systems — restricted original experiments, request permission for raw data.

## Evaluation warning
No synthetic values, foreign data or invented leak labels are included. The Nagpur observations are real published measurements but not raw logger exports. They cannot establish LeakLogic's detection rate: branch-endpoint flow pairs, corresponding geometry, stable supply cycles and confirmed leak/non-leak events are missing. For branch-level diagnostics the engine must refuse to compute accuracy until compatible labelled records are supplied. Refer to the Nagpur README for the published unit discrepancy and conversion assumptions. Original archives have NOT been bundled or downloaded; the script retrieves them on the user's machine.
