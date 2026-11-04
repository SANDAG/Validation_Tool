"""
Build the 2025 PeMS freeway counts input (same layout as source_Counts.xlsx) from
station_volume_speed_2025.csv, on the 2022 network.

Scope: PeMS mainline (ML) + HOV (HV) stations only. 2022 tab conventions are kept: no ramp
or auxiliary-lane links, GP links under 10,000 vehicles/day dropped.
  1. Stations already in the 2022 'freeway' tab keep their hwycovid (the lookup is the truth).
  2. Stations new in 2025 first get a free link by mutual-nearest matching (same route +
     direction + GP/HOV type, within 100 ft, link not used by a lookup station). A new station
     with no free link takes the nearest eligible link within 100 ft even if another station
     already holds it (several stations may share a link). Everything else is left out and
     listed on the 'excluded' sheet.
  3. As in 2022, GP links with count_day < 10,000 are dropped.

Sheets written: freeway, all_classes, lookup_review, excluded, station_status.
station_status covers every station in the T file (including ramps/connectors) and is what
build_station_map.py draws.
Usage: python build_source_counts_2025.py [--out OUTPUT_DIR]   (default: this folder)
"""

import argparse
import re
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely import wkt

T_CSV = r"T:\data\PeMS\station_volume_speed_2025.csv"
SCEN = r"T:\STORAGE-63T\2025RP_final\2022"
XLSX_2022 = SCEN + r"\analysis\validation\observed_data\source_Counts.xlsx"
NET_CSV = SCEN + r"\report\hwyTcad.csv"

TOL_FT = 100
MIN_GP_DAY = 10000      # 2022 rule: drop GP links with count_day below this
LOW_N_DAYS = 10         # flag only, not excluded
SCOPE = ["ML", "HV"]
DIR_CODE = {"NB": 1, "WB": 2, "SB": 3, "EB": 4}   # 2022 tab: dir code <-> dir_nm
DIR_LETTER = {"NB": "N", "SB": "S", "EB": "E", "WB": "W"}
COUNT_COLS = ["count_day", "count_ea", "count_am", "count_md", "count_pm", "count_ev"]
FREEWAY_COLS = ["station", "hwycovid", "corridor", "nm", "fxnm", "txnm", "dir", "dir_nm", "ifc",
                "ihov", "lkno", "rtno", "length", "city", "city_nm", "pmsa", "pmsa_nm",
                *COUNT_COLS, "source", "year"]
ALLCLASS_COLS = ["hwycovid", "dir", "dir_nm", "ifc", "ihov", "city", "city_nm", "pmsa", "pmsa_nm",
                 "count_day", "rdClass", "source", "year"]

ap = argparse.ArgumentParser()
ap.add_argument("--out", default=str(Path(__file__).resolve().parent))
args = ap.parse_args()
out_dir = Path(args.out)
out_dir.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
t_all = pd.read_csv(T_CSV)
t_all["station"] = t_all["station"].astype(int)
t = t_all[t_all["lane_type"].isin(SCOPE)].copy()
assert t["lat"].notna().all() and t["lon"].notna().all(), "station without coordinates"
print(f"T file: {len(t_all)} stations, {len(t)} ML/HV in scope")

x = pd.read_excel(XLSX_2022, sheet_name=None)
f22, a22 = x["freeway"], x["all_classes"]
lookup = dict(zip(f22["station"], f22["hwycovid"]))
assert f22["hwycovid"].is_unique and f22["station"].is_unique

net = pd.read_csv(NET_CSV, usecols=["ID", "NM", "FXNM", "TXNM", "FC", "HOV", "geometry"],
                  dtype={"ID": int}, low_memory=False)
net["geometry"] = net["geometry"].apply(wkt.loads)
net = gpd.GeoDataFrame(net, geometry="geometry", crs="EPSG:2230").set_index("ID", drop=False)

fw = net[net["FC"] == 1].copy()
fw["route"] = fw["NM"].str.extract(r"(\d+)")[0].astype(float)
fw["dir_nm"] = fw["NM"].str.extract(r"\b(NB|SB|EB|WB)\b")[0]
fw["typ"] = fw["HOV"].map(lambda h: "GP" if h == 1 else "HOV")
fw = fw.dropna(subset=["route", "dir_nm"])
fw["dir_letter"] = fw["dir_nm"].map(DIR_LETTER)

pts = gpd.GeoDataFrame(t, geometry=gpd.points_from_xy(t["lon"], t["lat"]),
                       crs="EPSG:4326").to_crs("EPSG:2230")
pts["typ"] = pts["lane_type"].map({"ML": "GP", "HV": "HOV"})
pts["in_lookup"] = pts["station"].isin(lookup)


def candidates(stations, links):
    rows, status, nearest = [], {}, {}
    for r in stations.itertuples():
        c = links[(links["route"] == r.freeway) & (links["dir_letter"] == r.direction)
                  & (links["typ"] == r.typ)]
        if c.empty:
            status[r.station] = "no candidate link (route/direction/type not in 2022 network)"
            continue
        d = c.geometry.distance(r.geometry)
        nearest[r.station] = float(d.min())
        w = c[d.values <= TOL_FT]
        if w.empty:
            status[r.station] = f"no link within {TOL_FT} ft (nearest {d.min():.0f} ft)"
            continue
        for link_id, dist in zip(w["ID"], w.geometry.distance(r.geometry)):
            rows.append((r.station, link_id, dist))
    return pd.DataFrame(rows, columns=["station", "link", "dist"]), status, nearest


def stable_match(c):
    """Mutual-nearest matching (same as pems_fwy-2022.ipynb match_station_to_link)."""
    pool, parts = c.copy(), []
    while len(pool):
        a = pool.loc[pool.groupby("station")["dist"].idxmin()]
        b = pool.loc[pool.groupby("link")["dist"].idxmin()]
        m = a.merge(b, on=["station", "link", "dist"])
        if m.empty:
            break
        parts.append(m)
        pool = pool[~pool["station"].isin(m["station"]) & ~pool["link"].isin(m["link"])]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["station", "link", "dist"])


# ---------------------------------------------------------------------------
# 1) Existing lookup stations: keep the 2022 hwycovid; re-match only as a sanity check
# ---------------------------------------------------------------------------
ex = pts[pts["in_lookup"]].copy()
ex["hwycovid"] = ex["station"].map(lookup)
c, _, _ = candidates(ex, fw)
re_ = stable_match(c)
rematch = dict(zip(re_["station"], re_["link"]))
rematch_dist = dict(zip(re_["station"], re_["dist"]))
ex["rematch_agrees"] = ex.apply(lambda r: rematch.get(r.station) == r.hwycovid, axis=1)
ex["match_dist_ft"] = ex.apply(
    lambda r: rematch_dist.get(r.station) if rematch.get(r.station) == r.hwycovid
    else fw.geometry.get(r.hwycovid).distance(r.geometry) if r.hwycovid in fw.index else None, axis=1)
print(f"existing lookup stations in T: {len(ex)}; re-match agrees for {int(ex['rematch_agrees'].sum())}")

# ---------------------------------------------------------------------------
# 2) New stations: stable match to a free 2022 freeway link within tolerance
# ---------------------------------------------------------------------------
free = fw[~fw["ID"].isin(set(ex["hwycovid"]))]
# The 2022 tab only has mainline/HOV link names (no auxiliary or local-access links), so new
# stations may only take links whose name already appears there.
nm_2022 = set(f22["nm"])
free = free[free["NM"].isin(nm_2022)]
print(f"free 2022 freeway links open to new stations: {len(free)}")
nw = pts[~pts["in_lookup"]].copy()
c, status, nearest = candidates(nw, free)
sm = stable_match(c)
nw_ok = nw[nw["station"].isin(sm["station"])].copy()
nw_ok["hwycovid"] = nw_ok["station"].map(dict(zip(sm["station"], sm["link"])))
nw_ok["match_dist_ft"] = nw_ok["station"].map(dict(zip(sm["station"], sm["dist"])))
nw_ok["rematch_agrees"] = pd.NA
nw_ok["shared_link"] = False
ex["shared_link"] = False

# 2b) Several stations may share a link: a new station that got no free link takes the nearest
# eligible 2022 freeway link within tolerance, even if another station already holds it.
left = nw[~nw["station"].isin(sm["station"])]
c2, _, _ = candidates(left, fw[fw["NM"].isin(nm_2022)])
if len(c2):
    near = c2.loc[c2.groupby("station")["dist"].idxmin()]
else:
    near = pd.DataFrame(columns=["station", "link", "dist"])
nw_shared = left[left["station"].isin(near["station"])].copy()
nw_shared["hwycovid"] = nw_shared["station"].map(dict(zip(near["station"], near["link"])))
nw_shared["match_dist_ft"] = nw_shared["station"].map(dict(zip(near["station"], near["dist"])))
nw_shared["rematch_agrees"] = pd.NA
nw_shared["shared_link"] = True
print(f"new stations sharing an already-used link: {len(nw_shared)}")

excluded = nw[~nw["station"].isin(sm["station"]) & ~nw["station"].isin(near["station"])].copy()

# Why each left-out station has no link. Distances here are to ALL same-route freeway links
# (not only the free ones), so "over 100 ft" means nothing of the right route/direction/type
# is within 100 ft; a link that is close but taken is reported as no match.
occupant = dict(zip(ex["hwycovid"], ex["station"]))


def explain(r):
    c = fw[(fw["route"] == r.freeway) & (fw["dir_letter"] == r.direction) & (fw["typ"] == r.typ)]
    if c.empty:
        return pd.Series({"reason": "no candidate link (route/direction/type not in 2022 network)",
                          "nearest_link_ft": None, "nearest_link_id": None})
    d = c.geometry.distance(r.geometry)
    link, ft = int(d.idxmin()), float(d.min())
    if ft > TOL_FT:
        reason = f"no same-route link within {TOL_FT} ft (nearest {ft:.0f} ft)"
    elif link in occupant:
        reason = f"nearest link {link} ({ft:.0f} ft) is already used by lookup station {occupant[link]}"
    elif fw.loc[link, "NM"] not in nm_2022:
        reason = f"nearest link {link} ({ft:.0f} ft) is an auxiliary/local-access link, not used in 2022"
    else:
        reason = f"lost link {link} ({ft:.0f} ft) to a closer new station"
    return pd.Series({"reason": reason, "nearest_link_ft": ft, "nearest_link_id": link})


excluded = pd.concat([excluded, excluded.apply(explain, axis=1)], axis=1)
print(f"new stations: {len(nw)}; matched {len(nw_ok)}; excluded {len(excluded)}")

sel = pd.concat([ex, nw_ok, nw_shared], ignore_index=True)
assert sel["station"].is_unique
sel["hwycovid"] = sel["hwycovid"].astype(int)
# stations on the same link, for the review sheet and the map
by_link = sel.groupby("hwycovid")["station"].apply(list)
sel["shares_link_with"] = [", ".join(str(s) for s in by_link[h] if s != st_) for h, st_ in
                           zip(sel["hwycovid"], sel["station"])]
print(f"stations: {len(sel)} on {sel['hwycovid'].nunique()} links")

# ---------------------------------------------------------------------------
# 3) Descriptive columns: copy from 2022 tab for lookup stations, network for new stations
# ---------------------------------------------------------------------------
desc22 = f22.set_index("station")
link22 = f22.drop_duplicates("hwycovid").set_index("hwycovid")   # descriptive columns by link
DESC_COLS = ["corridor", "nm", "fxnm", "txnm", "dir", "dir_nm", "ifc", "ihov", "lkno", "rtno", "length",
             "city", "city_nm", "pmsa", "pmsa_nm"]
known = a22[["hwycovid", "city", "city_nm", "pmsa", "pmsa_nm"]].drop_duplicates("hwycovid")
known = known.merge(net[["geometry"]].rename_axis("hwycovid_idx").reset_index(),
                    left_on="hwycovid", right_on="hwycovid_idx").drop(columns="hwycovid_idx")
known = gpd.GeoDataFrame(known, geometry="geometry", crs="EPSG:2230").reset_index(drop=True)


def nearest_known(link_geom, exclude_id=None):
    k = known if exclude_id is None else known[known["hwycovid"] != exclude_id]
    d = k.geometry.distance(link_geom)
    i = d.idxmin()
    return k.loc[i, ["city", "city_nm", "pmsa", "pmsa_nm"]], d.loc[i]


# how reliable is "city/pmsa of the nearest known link"? leave-one-out on the lookup links
loo = [(nearest_known(net.loc[h, "geometry"], exclude_id=h)[0], f22.set_index("hwycovid").loc[h])
       for h in f22["hwycovid"]]
city_ok = sum(int(p["city"] == a["city"]) for p, a in loo)
pmsa_ok = sum(int(p["pmsa"] == a["pmsa"]) for p, a in loo)
print(f"nearest-known-link inference, leave-one-out on 2022 lookup links: "
      f"city right {city_ok}/{len(loo)}, pmsa right {pmsa_ok}/{len(loo)}")

# length: geometry length in feet (checked against the 2022 tab below)
len_check = (net.loc[f22["hwycovid"], "geometry"].length.values - f22["length"].values)
print(f"geometry length vs 2022 'length': within 1 ft for {int((abs(len_check) <= 1).sum())}/{len(f22)}")

corr_by_nm = f22.groupby("nm")["corridor"].first().to_dict()
next_corr = int(f22["corridor"].max()) + 1
rows, notes = [], []
for r in sel.itertuples():
    note = []
    if r.in_lookup:
        d = desc22.loc[r.station]
        row = {c: d[c] for c in DESC_COLS}
    elif r.hwycovid in link22.index:
        # the link already has a row in the 2022 tab (held by another or a retired station)
        d = link22.loc[r.hwycovid]
        row = {c: d[c] for c in DESC_COLS}
        note.append("descriptive columns copied from the 2022 row for this link")
    else:
        n = net.loc[r.hwycovid]
        dn = fw.loc[r.hwycovid, "dir_nm"]
        if n["NM"] in corr_by_nm:
            corridor = corr_by_nm[n["NM"]]
        else:
            corridor = next_corr
            corr_by_nm[n["NM"]] = corridor
            next_corr += 1
            note.append("new corridor number")
        kn, kd = nearest_known(n["geometry"])
        note.append(f"city/pmsa inferred from nearest known link ({kd:.0f} ft)")
        row = {"corridor": corridor, "nm": n["NM"], "fxnm": n["FXNM"], "txnm": n["TXNM"],
               "dir": DIR_CODE[dn], "dir_nm": dn, "ifc": int(n["FC"]), "ihov": int(n["HOV"]),
               "lkno": pd.NA, "rtno": pd.NA, "length": float(n["geometry"].length),
               "city": kn["city"], "city_nm": kn["city_nm"], "pmsa": kn["pmsa"], "pmsa_nm": kn["pmsa_nm"]}
    row.update({"station": r.station, "hwycovid": r.hwycovid, "source": "PeMS", "year": 2025})
    for cc in COUNT_COLS:
        row[cc] = int(round(getattr(r, cc)))
    rows.append(row)
    notes.append("; ".join(note))

full = pd.DataFrame(rows)
review = sel[["station", "hwycovid", "lane_type", "freeway", "direction", "name", "n_days",
              "match_dist_ft", "rematch_agrees", "pct_change_2022_2025", "in_lookup", "shared_link",
              "shares_link_with"]].copy()
review["origin"] = ["2022 lookup" if a else "new, shares a link" if b else "new stable match"
                    for a, b in zip(review["in_lookup"], review["shared_link"])]
review["notes"] = notes
review["flag_low_n_days"] = review["n_days"] < LOW_N_DAYS
review = review.drop(columns=["in_lookup", "shared_link"])

# ---------------------------------------------------------------------------
# 4) 2022 rule: drop GP links with a low daily count
# ---------------------------------------------------------------------------
low = (full["ihov"] == 1) & (full["count_day"] < MIN_GP_DAY)
review["dropped_gp_under_10k"] = low.values
dropped_low = full[low]
full = full[~low].sort_values("hwycovid").reset_index(drop=True)
print(f"dropped GP count_day < {MIN_GP_DAY:,}: {int(low.sum())}")

freeway = full[FREEWAY_COLS]
all_classes = freeway.assign(rdClass="Freeway", count_day=freeway["count_day"].astype(float))[ALLCLASS_COLS]
excl = excluded[["station", "lane_type", "freeway", "direction", "name", "n_days", "count_day",
                 "reason", "nearest_link_id", "nearest_link_ft"]]
excl = pd.concat([excl, dropped_low.assign(reason=f"GP link with count_day < {MIN_GP_DAY:,}")
                  [["station", "count_day", "reason"]]], ignore_index=True)
# ---------------------------------------------------------------------------
# 5) Status of every station in the T file, for the map
#    lookup_existing / good_match / over_100ft / no_match / out_of_scope (ramps, connectors)
# ---------------------------------------------------------------------------
st = t_all[["station", "name", "lane_type", "freeway", "direction", "lat", "lon", "n_days",
            "count_day"]].copy()
sel_idx = sel.set_index("station")
ex_ids = set(ex["station"])
ok_ids = set(nw_ok["station"]) | set(nw_shared["station"])
reason = dict(zip(excluded["station"], excluded["reason"]))


def classify(station, lane_type):
    if station in ex_ids:
        return "lookup_existing"
    if station in ok_ids:
        return "good_match"
    if station in reason:
        return "over_100ft" if reason[station].startswith("no same-route link within") else "no_match"
    return "out_of_scope"


st["status"] = [classify(s, lt) for s, lt in zip(st["station"], st["lane_type"])]
st["hwycovid"] = st["station"].map(sel_idx["hwycovid"])
st["match_dist_ft"] = st["station"].map(sel_idx["match_dist_ft"]).astype(float).round(1)
st["nearest_link_ft"] = st["station"].map(dict(zip(excluded["station"], excluded["nearest_link_ft"]))).astype(float).round(0)
st["nearest_link_id"] = st["station"].map(dict(zip(excluded["station"], excluded["nearest_link_id"]))).astype("Int64")
st["detail"] = st["station"].map(reason)
st.loc[st["status"] == "out_of_scope", "detail"] = "ramp / connector: not matched (freeway mainline and HOV only)"
st["shares_link_with"] = st["station"].map(sel_idx["shares_link_with"]).fillna("")
st["dropped_gp_under_10k"] = st["station"].isin(set(dropped_low["station"]))
st["flag_low_n_days"] = st["n_days"] < LOW_N_DAYS

out_xlsx = out_dir / "source_Counts_2025.xlsx"
with pd.ExcelWriter(out_xlsx) as w:
    freeway.to_excel(w, sheet_name="freeway", index=False)
    all_classes.to_excel(w, sheet_name="all_classes", index=False)
    review.sort_values(["origin", "station"]).to_excel(w, sheet_name="lookup_review", index=False)
    excl.to_excel(w, sheet_name="excluded", index=False)
    st.sort_values(["status", "station"]).to_excel(w, sheet_name="station_status", index=False)

print(f"\nfreeway rows: {len(freeway)} (2022 lookup {int(freeway['station'].isin(lookup).sum())}, "
      f"new {int((~freeway['station'].isin(lookup)).sum())}) on {freeway['hwycovid'].nunique()} links; "
      f"rows on a shared link: {int(freeway['hwycovid'].duplicated(keep=False).sum())}")
print(f"flagged n_days < {LOW_N_DAYS}: {int(review['flag_low_n_days'].sum())}")
print("station_status:", st["status"].value_counts().to_dict())
print(f"Saved {out_xlsx}")
