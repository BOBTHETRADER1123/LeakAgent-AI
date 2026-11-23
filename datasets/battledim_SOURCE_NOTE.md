# BattLeDIM source and provenance

Publisher record: https://zenodo.org/records/4017659
Organizer data page: https://battledim.ucy.ac.cy/?page_id=33

BattLeDIM is an international L-Town water-distribution benchmark, not an Indian utility dataset. Its SCADA time series are sampled every five minutes. The official metadata identifies pressure sensors in metres of head, flow sensors in cubic metres per hour, tank level in metres, and AMR demand in litres per hour. Leakage time series are a separate data product, with units of cubic metres per hour. The dataset configuration contains leakage scenario information. Review the publisher README and configuration before interpreting each year as training or evaluation data.

The project ZIP does not include the full BattLeDIM archive. The original archive is about 550.5 MB on Zenodo. Upload original publisher CSVs in the Streamlit BattLeDIM benchmark workspace. The importer preserves source filenames and sensor IDs and does not infer chainage or create fake observations. The simple historical z-score comparison is exploratory only; it is not an official BattLeDIM scoring implementation and does not prove that an anomaly is a leak.
