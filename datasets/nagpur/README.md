# Nagpur Ramnagar published field data
Source: Jadhao, R.D. & Gupta, R. (2018), Calibration of water distribution network of the Ramnagar zone in Nagpur City using online pressure and flow data, Applied Water Science 8:29, Table 1. https://doi.org/10.1007/s13201-018-0672-3
Original article: https://d-nb.info/1160291187/34
Licence: CC BY 4.0 https://creativecommons.org/licenses/by/4.0/
Changes: manually transcribed table values into CSV, added ISO timestamps with assumed Indian local timezone, converted flow and pressure units in separate CSV; SQLite contains converted data. This is published data, not the original raw logger file. Independent transcription review still recommended.

Table 1 prints m3/s in its flow heading, but the article text explicitly reports the daily mean of 504.44 m3/h and total supply 12.107 MLD. The first 24 published hourly values average 504.443, so the normalized file interprets these values as m3/h. This correction is documented, not silently applied to the raw transcription. The final midnight row repeats the starting values and is retained as a published boundary observation, not an independent day. Pressure heads in metres are converted to kPa using density 1000 kg/m3 and g=9.81 m/s2. HGL is not gauge pressure. The three pressure points are not paired branch endpoints.

No confirmed leak labels, paired upstream/downstream flows, or full pipe geometry are provided here. Null labels mean unknown, not normal. Do not calculate leak detection accuracy from these records. The network was converted to continuous supply in 2007; do not treat these data as intermittent cycles.
