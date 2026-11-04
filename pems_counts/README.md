# 2025 PeMS counts

Builds 2025 freeway counts from the PeMS pipeline output and shows them in the Validation Tool.
Scope for now: PeMS mainline (ML) and HOV (HV) stations, on the 2022 network and model run.

Input: `T:\data\PeMS\station_volume_speed_2025.csv` (PeMS-Pipeline `output/`).
Run each script with the project environment, e.g. `python pems_counts\build_source_counts_2025.py`.

| Step | Script | Output |
| --- | --- | --- |
| 1 | `build_source_counts_2025.py` | `source_Counts_2025.xlsx`: `freeway` and `all_classes` in the 2022 `source_Counts.xlsx` layout, plus `lookup_review`, `excluded` and `station_status` |
| 2 | `build_pems2025_scenario.py` | scenario folder `T:\data\PeMS\scenario_pems2025` (worksheets, reduced `hwyTcad.csv`); listed in `config.yaml` |
| 3 | `build_station_map.py` | `station_match_map.html`: all 2025 stations and the freeway network, coloured by match status |
How stations get a `hwycovid`:
- Stations in the 2022 `freeway` tab keep their `hwycovid` (the lookup is the source of truth).
- New stations first match a free 2022 freeway link with the same route, direction and GP/HOV type within
  100 ft (mutual nearest, as in `pems_fwy-2022.ipynb`). A new station with no free link takes the nearest
  eligible link within 100 ft even if another station already holds it, so a link can have several stations
  (`shares_link_with` on `lookup_review`). Anything else is left out and listed on `excluded`.
- GP links under 10,000 vehicles/day are dropped, as in 2022.

Model columns in the scenario worksheets are rebuilt from the 2022 scenario's `report/hwyLoad.shp`; the script
checks that it reproduces the 2022 worksheet before writing the 2025 one. Trucks, transit and regional VMT are
copied unchanged from 2022.
