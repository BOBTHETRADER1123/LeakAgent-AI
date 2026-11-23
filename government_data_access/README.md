# LeakLogic AI 4.5 — Hyderabad government-data acquisition pack

## Important data-status statement
This package does **not** contain HMWSSB SCADA/pressure/flow/leak-repair records. Those operational records are not confirmed as publicly downloadable. They must be requested from HMWSSB and supplied with authorization. No values in the templates are represented as government observations.

## Primary target: HMWSSB
Request anonymized historical records for one distribution zone: synchronized timestamps; pressure and flow with units and calibration metadata; GIS/chainage, pipe diameter/material/length/elevation; pump/valve/reservoir/tank states; supply cycles; confirmed leak and repair records; and normal-operation periods. Ask for CSV/Excel exports and a data dictionary. Request written permission for academic analysis. Do not upload personal/customer data.

## Official/public starting points
- HMWSSB: https://www.hyderabadwater.gov.in/
- HMWSSB datasets indexed on OpenCity: https://data.opencity.in/dataset/?organization=hyderabad-metropolitan-water-supply-and-sewerage-board-hmwssb
- National Water Data Portal: https://nwdp.nwic.gov.in/
- Telangana Open Data Portal: https://data.telangana.gov.in/

These portals may contain administrative, water-resource or infrastructure data. Their existence does not mean they contain synchronized pipeline sensor records required for leak localization. Verify each file's metadata, publisher, licence, date range and units.

The CSVs in `templates/` are empty schemas, not observations. Fill them only from authorized original records. Leak location is bounded by sensor spacing unless an independently validated localization technology is supplied. Do not report accuracy until ground-truth leak and normal labels are verified.
