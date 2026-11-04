"""
Build a local scenario folder that makes the Validation Tool show the 2025 PeMS freeway counts
against the 2022 model run (the 2022 network and model flows are kept; trucks, transit and
regional VMT are copied unchanged from the 2022 scenario).

Reads  : source_Counts_2025.xlsx (build_source_counts_2025.py) + the 2022 scenario on the T drive
Writes : <out>/analysis/validation/vis_worksheet - {fwy,allclass,truck,board}_worksheet.csv,
         <out>/analysis/validation/vis_worksheet - regional_vmt.csv,
         <out>/report/hwyTcad.csv (only the links the worksheets use) and transitRoute.csv,
         <out>/output/datalake_metadata.yaml
Then add <out> to LOCAL_SCENARIO_LIST in config.yaml.

The model columns are rebuilt from the 2022 scenario's report/hwyLoad.shp. Before using them for
2025 the same code is run on the 2022 counts and compared with the 2022 worksheet.
Usage: python build_pems2025_scenario.py [--out SCENARIO_DIR]
"""

import argparse
import shutil
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SCEN = Path(r"T:\STORAGE-63T\2025RP_final\2022")
VAL = SCEN / "analysis" / "validation"
COUNTS_2025 = HERE / "source_Counts_2025.xlsx"
DEFAULT_OUT = r"T:\data\PeMS\scenario_pems2025"
SCENARIO_ID = 2025
SCENARIO_TITLE = "2025 PeMS counts (2022 network and model)"
SCENARIO_YEAR = 2025

P = ["ea", "am", "md", "pm", "ev"]
VCAT_BINS = [0, 10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000, np.inf]
VCAT_LABELS = ["0~10,000", "10,000~20,000", "20,000~30,000", "30,000~40,000", "40,000~50,000",
               "50,000~60,000", "60,000~70,000", "70,000~80,000", "80,000~90,000",
               "90,000~100,000", "> 100,000"]

ap = argparse.ArgumentParser()
ap.add_argument("--out", default=DEFAULT_OUT)
args = ap.parse_args()
out = Path(args.out)

fw22 = pd.read_csv(VAL / "vis_worksheet - fwy_worksheet.csv")
ac22 = pd.read_csv(VAL / "vis_worksheet - allclass_worksheet.csv")
shp = gpd.read_file(SCEN / "report" / "hwyLoad.shp", ignore_geometry=True).set_index("hwycov_id")


def pct(model, obs, ndigits=1):
    return (((model - obs) / obs.where(obs != 0)) * 100).round(ndigits)


def fwy_worksheet(counts):
    """counts: the 'freeway' tab layout (station..year). Returns the fwy_worksheet layout."""
    d = counts.copy()
    m = shp.loc[d["hwycovid"]].reset_index(drop=True)
    d["traffic_metric"] = "fwyCount"
    d["len_mile"] = m["len_mile"].values
    for p in P:
        d[f"{p.upper()}_Flow"] = m[f"ab_{p}_flow"].round().astype("int64").values
        d[f"{p.upper()}_Speed"] = m[f"ab_{p}_mph"].round().astype("int64").values
        d[f"{p.upper()}_Vmt"] = (d[f"{p.upper()}_Flow"] * d["len_mile"]).round().astype("int64")
    d["DAY_Flow"] = sum(d[f"{p.upper()}_Flow"] for p in P)
    d["DAY_Speed"] = (sum(d[f"{p.upper()}_Speed"] for p in P) / 5).round(1)
    d["DAY_Vmt"] = sum(d[f"{p.upper()}_Vmt"] for p in P)
    d["TruckFlow"] = m["abTrucFlow"].round(1).values
    d["lhdTruckFlow"] = m["abLhdFlow"].round(1).values
    d["mhdTruckFlow"] = m["abMhdFlow"].round(1).values
    d["hhdTruckFlow"] = m["abHhdFlow"].round(1).values
    for p in ["day", *P]:
        up = p.upper()
        d[f"vmt_{p}"] = (d[f"count_{p}"] * d["len_mile"]).round().astype("int64")
        d[f"gap_{p}"] = pct(d[f"{up}_Flow"], d[f"count_{p}"])
        d[f"vmt_gap_{p}"] = pct(d[f"{up}_Vmt"], d[f"vmt_{p}"])
    d["vis_order"] = range(len(d))
    return d[list(fw22.columns)]


ALLCLASS_INPUT = ["hwycovid", "dir", "dir_nm", "ifc", "ihov", "city", "city_nm", "pmsa", "pmsa_nm",
                  "count_day", "rdClass", "source", "year"]
RD_ID = {"Freeway": 1, "Ramp": 2, "Arterial": 3, "Collector": 4}


def allclass_worksheet(df):
    """df: the 'all_classes' tab layout. Model flow is the link's two-direction total (ab + ba, which is
    just ab on one-way freeways and ramps), summed over the five periods."""
    d = df[ALLCLASS_INPUT].copy()
    m = shp.loc[d["hwycovid"]].reset_index(drop=True)
    d["count_day"] = d["count_day"].astype(float)
    d["len_mile"] = m["len_mile"].values
    flow = {p: (m[f"ab_{p}_flow"] + m[f"ba_{p}_flow"]).round().astype("int64").values for p in P}
    d["DAY_Flow"] = sum(flow.values())
    d["DAY_Vmt"] = sum((flow[p] * d["len_mile"]).round().astype("int64") for p in P)
    d["vmt_day"] = (d["count_day"] * d["len_mile"]).round().astype("int64")
    d["gap_day"] = pct(d["DAY_Flow"], d["count_day"])
    d["vmt_gap_day"] = pct(d["DAY_Vmt"], d["vmt_day"])
    d["rdClassID"] = d["rdClass"].map(RD_ID)
    cat = pd.cut(d["DAY_Flow"], bins=VCAT_BINS, labels=False, right=False)
    d["vcategory_id"] = (cat + 1).astype(float)
    d["vcategory"] = cat.map(dict(enumerate(VCAT_LABELS)))
    d["vis_order"] = range(len(d))
    return d[list(ac22.columns)]


# ---------------------------------------------------------------------------
# Self-check: rebuild the 2022 worksheets from the 2022 counts and compare
# ---------------------------------------------------------------------------
counts22 = fw22[list(pd.read_excel(COUNTS_2025, sheet_name="freeway").columns)]
re22 = fwy_worksheet(counts22)
print("self-check on the 2022 fwy worksheet (share of rows equal, tolerance 0.06):")
bad = []
for c in fw22.columns:
    if c in counts22.columns or c == "vis_order":   # vis_order is a row index the app doesn't use
        continue
    a, b = fw22[c], re22[c]
    if pd.api.types.is_numeric_dtype(a):
        rate = float(((a - b).abs() <= 0.06).mean())
    else:
        rate = float((a == b).mean())
    if rate < 0.99:
        bad.append((c, round(rate, 3)))
print("  columns below 99%:", bad or "none")
acre = allclass_worksheet(ac22)
print(f"self-check on the 2022 all_classes worksheet ({len(ac22)} rows, every road class):")
bad = []
for c in ac22.columns:
    if c in ALLCLASS_INPUT or c == "vis_order":
        continue
    a, b = ac22[c], acre[c]
    rate = float(((a - b).abs() <= 0.06).mean()) if pd.api.types.is_numeric_dtype(a) else float((a == b).mean())
    if rate < 0.99:
        bad.append((c, round(rate, 3)))
print("  columns below 99%:", bad or "none")

# ---------------------------------------------------------------------------
# 2025 worksheets
# ---------------------------------------------------------------------------
counts25 = pd.read_excel(COUNTS_2025, sheet_name="freeway")
fwy25 = fwy_worksheet(counts25)
ac25 = allclass_worksheet(pd.read_excel(COUNTS_2025, sheet_name="all_classes"))
print(f"\n2025: fwy_worksheet {fwy25.shape}, all_classes {ac25.shape}, "
      f"links without model flow: {int((fwy25['DAY_Flow'] <= 0).sum())}")

val_out = out / "analysis" / "validation"
rep_out = out / "report"
meta_out = out / "output"
for p_ in (val_out, rep_out, meta_out):
    p_.mkdir(parents=True, exist_ok=True)

fwy25.to_csv(val_out / "vis_worksheet - fwy_worksheet.csv", index=False)
ac25.to_csv(val_out / "vis_worksheet - allclass_worksheet.csv", index=False)
for name in ("truck_worksheet", "board_worksheet", "regional_vmt"):
    shutil.copy2(VAL / f"vis_worksheet - {name}.csv", val_out / f"vis_worksheet - {name}.csv")

# Map geometry: only the links the worksheets use. Column positions matter to load_data.py
# (dtype={7: str, 8: str} = FXNM, TXNM), so keep the first nine columns of hwyTcad.csv.
truck = pd.read_csv(VAL / "vis_worksheet - truck_worksheet.csv")
ids = set(ac25["hwycovid"]) | set(truck["hwycovid"].dropna().astype(int)) | \
    set(truck.get("hwycovid_2", pd.Series(dtype=float)).dropna().astype(int))
tcad = pd.read_csv(SCEN / "report" / "hwyTcad.csv", low_memory=False, dtype={"ID": int})
keep = list(tcad.columns[:9]) + ["geometry"]
tcad = tcad.loc[tcad["ID"].isin(ids), keep]
tcad.to_csv(rep_out / "hwyTcad.csv", index=False)
shutil.copy2(SCEN / "report" / "transitRoute.csv", rep_out / "transitRoute.csv")
print(f"hwyTcad.csv: {len(tcad)} links kept for {len(ids)} ids")

(meta_out / "datalake_metadata.yaml").write_text(
    f"scenario_id: {SCENARIO_ID}\nscenario_title: '{SCENARIO_TITLE}'\nscenario_year: '{SCENARIO_YEAR}'\n",
    encoding="utf-8")
print(f"Scenario written to {out}")
