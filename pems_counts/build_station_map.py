"""
Build station_match_map.html: every 2025 PeMS station on the 2022 freeway network, coloured by
how it was handled by build_source_counts_2025.py.

  lookup_existing  station already in the 2022 station -> hwycovid lookup (kept)
  good_match       new station matched to a 2022 freeway link within 100 ft (included); several
                   stations may share one link, and the popup says so
  over_100ft       new station with no same-route 2022 freeway link within 100 ft (left out)
  no_match         new station with no candidate link at all for its route, direction and type
                   (or only auxiliary-lane links nearby)
  out_of_scope     ramps / connectors, not matched (this tool covers freeway mainline and HOV)

Reads  : source_Counts_2025.xlsx (station_status + freeway sheets) and the 2022 hwyTcad.csv
Writes : station_match_map.html (self-contained; Leaflet and map tiles load from the internet)
Usage  : python build_station_map.py
"""

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely import wkt

HERE = Path(__file__).resolve().parent
XLSX = HERE / "source_Counts_2025.xlsx"
NET_CSV = r"T:\STORAGE-63T\2025RP_final\2022\report\hwyTcad.csv"
OUT = HERE / "station_match_map.html"
SIMPLIFY_FT = 10

st = pd.read_excel(XLSX, sheet_name="station_status")
fwy = pd.read_excel(XLSX, sheet_name="freeway")
with_count = fwy.groupby("hwycovid")["station"].apply(lambda s: [int(x) for x in s]).to_dict()

# ---- network: freeway links (FC == 1), simplified, in lat/lon --------------------------------
net = pd.read_csv(NET_CSV, usecols=["ID", "NM", "FC", "geometry"], dtype={"ID": int}, low_memory=False)
net = net[net["FC"] == 1].copy()
net["geometry"] = net["geometry"].apply(wkt.loads)
g = gpd.GeoDataFrame(net, geometry="geometry", crs="EPSG:2230")
g["geometry"] = g.geometry.simplify(SIMPLIFY_FT)
g = g.to_crs("EPSG:4326")


def lines(geom):
    parts = geom.geoms if geom.geom_type == "MultiLineString" else [geom]
    return [[[round(y, 5), round(x, 5)] for x, y in p.coords] for p in parts]


links = [{"id": int(r.ID), "nm": r.NM, "xy": lines(r.geometry),
          "stations": with_count.get(r.ID, [])}
         for r in g.itertuples()]

# ---- stations ---------------------------------------------------------------------------------
st = st.dropna(subset=["lat", "lon"]).copy()
cols = ["station", "name", "lane_type", "freeway", "direction", "lat", "lon", "n_days", "count_day",
        "status", "hwycovid", "match_dist_ft", "nearest_link_ft", "nearest_link_id", "shares_link_with",
        "detail",
        "dropped_gp_under_10k",
        "flag_low_n_days"]
stations = json.loads(st[cols].to_json(orient="records"))

data = {"stations": stations, "links": links}
html = TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>2025 PeMS Station Matches</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<style>
  :root { --bg:#ffffff; --fg:#1f2933; --muted:#5f6b7a; --line:#d8dee6; --card:#ffffff; --mapbg:#e8ecef; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#1c2127; --fg:#e6eaef; --muted:#9aa5b1; --line:#39424d; --card:#252c34; --mapbg:#2a3139; }
  }
  html, body { height:100%; margin:0; background:var(--bg); color:var(--fg);
               font:14px/1.4 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
  #map { position:absolute; inset:0; background:var(--mapbg); }
  #notice { color:#b45309; font-size:12px; margin-top:4px; }
  #notice:empty { display:none; }
  #panel { position:absolute; z-index:1000; top:12px; right:12px; width:300px; max-height:calc(100% - 24px);
           overflow:auto; background:var(--card); color:var(--fg); border:1px solid var(--line);
           border-radius:8px; padding:12px 14px; box-shadow:0 2px 10px rgba(0,0,0,.18); }
  #panel h1 { font-size:15px; margin:0 0 2px; }
  #panel .sub { color:var(--muted); font-size:12px; margin:0 0 10px; }
  .head { display:flex; justify-content:space-between; align-items:flex-start; gap:8px; }
  #tog { flex:none; width:28px; height:28px; border:1px solid var(--line); border-radius:6px;
         background:var(--bg); color:var(--fg); font-size:16px; line-height:1; cursor:pointer; }
  #panel.min #pbody { display:none; }
  #panel.min .sub { margin-bottom:0; }
  .row { display:flex; align-items:center; gap:8px; padding:3px 0; cursor:pointer; }
  .row input { margin:0; }
  .dot { width:12px; height:12px; border-radius:50%; flex:none; border:1px solid rgba(0,0,0,.35); }
  .bar { width:18px; height:0; flex:none; border-top:3px solid; }
  .row .n { margin-left:auto; color:var(--muted); font-variant-numeric:tabular-nums; }
  .sec { font-size:11px; text-transform:uppercase; letter-spacing:.04em; color:var(--muted); margin:10px 0 2px; }
  #q { width:100%; box-sizing:border-box; padding:6px 8px; border:1px solid var(--line); border-radius:6px;
       background:var(--bg); color:var(--fg); }
  #msg { color:var(--muted); font-size:12px; min-height:16px; margin-top:3px; }
  details { margin-top:10px; font-size:12px; color:var(--muted); }
  details p { margin:4px 0; }
  .pop b { font-weight:600; }
  .pop .tag { display:inline-block; padding:0 6px; border-radius:9px; color:#fff; font-size:11px; }
  .pop .meta { color:#5f6b7a; }
  @media (max-width: 600px) { #panel { width:auto; left:12px; max-height:45%; } }
</style>
</head>
<body>
<div id="map"></div>
<aside id="panel">
  <div class="head">
    <div><h1>2025 PeMS stations</h1><p class="sub">on the 2022 freeway network</p></div>
    <button id="tog" type="button" aria-expanded="true" aria-controls="pbody" title="Show or hide the legend">&minus;</button>
  </div>
  <div id="pbody">
  <div class="sec">Stations</div>
  <div id="legend"></div>
  <div class="sec">Network</div>
  <label class="row"><input type="checkbox" id="lnkUsed" checked><span class="bar" style="border-color:#1b4f8a"></span>
    <span>Link with a Valid 2025 PeMS Station</span><span class="n" id="nUsed"></span></label>
  <label class="row"><input type="checkbox" id="lnkOther" checked><span class="bar" style="border-color:#aab2bd"></span>
    <span>Other freeway link</span><span class="n" id="nOther"></span></label>
  <div id="notice" role="status"></div>
  <div class="sec">Find</div>
  <input id="q" type="search" placeholder="Station ID or hwycovid" aria-label="Station ID or hwycovid">
  <div id="msg"></div>
  <details>
    <summary>What the colours mean</summary>
    <p><b>Lookup existing</b>: station is in the 2022 station-to-hwycovid lookup, which is kept as is.</p>
    <p><b>Good match</b>: new station matched to a 2022 freeway link within 100 ft (same route,
      direction and GP/HOV type). Several stations can share one link.</p>
    <p><b>Over 100 ft</b>: new station with no such link within 100 ft. Left out.</p>
    <p><b>No match</b>: new station with no candidate link for its route, direction and type.</p>
    <p><b>Ramp / connector</b>: not matched in this pass (mainline and HOV only).</p>
    <p>Click a station to highlight its link.</p>
  </details>
  </div>
</aside>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script>
if (!window.L) {
  document.getElementById("map").innerHTML = '<p style="padding:24px;max-width:520px;color:var(--fg)">' +
    'The map library (Leaflet) could not be loaded from cdnjs.cloudflare.com. It is probably blocked on this network.</p>';
  throw new Error("Leaflet not loaded");
}
const DATA = __DATA__;
const ORDER = ["out_of_scope", "no_match", "over_100ft", "good_match", "lookup_existing"]; // draw order
const COLORS = {lookup_existing:"#2b83ba", good_match:"#1a9850", over_100ft:"#f28e2b",
                no_match:"#d62728", out_of_scope:"#9aa0a6"};
const LABELS = {lookup_existing:"Lookup existing", good_match:"Good match", over_100ft:"Over 100 ft",
                no_match:"No match", out_of_scope:"Ramp / connector (not matched)"};
// keep popups clear of the legend card (right edge on wide screens, top edge on narrow ones)
const POP = () => window.innerWidth >= 700
  ? {autoPanPaddingTopLeft:[20, 20], autoPanPaddingBottomRight:[330, 20]}
  : {autoPanPaddingTopLeft:[20, 120], autoPanPaddingBottomRight:[20, 20]};
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const num = v => (v === null || v === undefined) ? "" : Number(v).toLocaleString();

const map = L.map("map", {preferCanvas:true, zoomControl:true}).setView([32.85, -117.05], 10);
// Base map: Esri World Light Gray. If no tile loads (blocked or offline), drop to a plain background.
const noticeEl = document.getElementById("notice");
let tilesOk = 0, tilesBad = 0;
const tiles = L.tileLayer(
  "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
  {maxNativeZoom:16, maxZoom:19, attribution:"Tiles &copy; Esri"}).addTo(map);
tiles.on("tileload", () => { tilesOk++; });
tiles.on("tileerror", () => {
  tilesBad++;
  if (!tilesOk && tilesBad >= 4 && map.hasLayer(tiles)) {
    map.removeLayer(tiles);
    noticeEl.textContent = "Base map tiles could not be loaded (blocked or offline). Showing the network on a plain background.";
  }
});
map.createPane("links").style.zIndex = 410;
map.createPane("stations").style.zIndex = 450;

// ---- network ----
const linkLayers = {}, usedGroup = L.layerGroup(), otherGroup = L.layerGroup();
const baseStyle = l => l.stations.length ? {color:"#1b4f8a", weight:3, opacity:.85} : {color:"#aab2bd", weight:2, opacity:.8};
DATA.links.forEach(l => {
  const pl = L.polyline(l.xy, Object.assign({pane:"links"}, baseStyle(l)));
  pl.bindPopup(`<div class="pop"><b>Link ${esc(l.id)}</b><br>${esc(l.nm)}<br>` +
    (l.stations.length ? `2025 count from station${l.stations.length > 1 ? "s" : ""} ${esc(l.stations.join(", "))}`
                       : `<span class="meta">No 2025 count on this link</span>`) + `</div>`, POP());
  pl._link = l; linkLayers[l.id] = pl;
  (l.stations.length ? usedGroup : otherGroup).addLayer(pl);
});
usedGroup.addTo(map); otherGroup.addTo(map);
document.getElementById("nUsed").textContent = DATA.links.filter(l => l.stations.length).length;
document.getElementById("nOther").textContent = DATA.links.filter(l => !l.stations.length).length;
document.getElementById("lnkUsed").onchange = e => e.target.checked ? usedGroup.addTo(map) : map.removeLayer(usedGroup);
document.getElementById("lnkOther").onchange = e => e.target.checked ? otherGroup.addTo(map) : map.removeLayer(otherGroup);

let lit = null;
function highlight(hwycovid, color) {
  if (lit) { lit.setStyle(baseStyle(lit._link)); lit = null; }
  const pl = hwycovid != null ? linkLayers[hwycovid] : null;
  if (pl) { pl.setStyle({color:color, weight:7, opacity:1}); pl.bringToFront(); lit = pl; }
}
map.on("click", () => highlight(null));

// ---- stations ----
const groups = {}, markers = {}, counts = {};
ORDER.forEach(s => { groups[s] = L.layerGroup(); counts[s] = 0; });
function popup(d) {
  const c = COLORS[d.status];
  let h = `<div class="pop"><b>Station ${esc(d.station)}</b> <span class="tag" style="background:${c}">${esc(LABELS[d.status])}</span><br>` +
          `${esc(d.name)}<br><span class="meta">${esc(d.freeway)} ${esc(d.direction)} &middot; ${esc(d.lane_type)}</span><br>`;
  if (d.hwycovid != null) h += `Link (hwycovid): <b>${esc(d.hwycovid)}</b>` +
        (d.match_dist_ft != null ? ` &middot; ${esc(d.match_dist_ft)} ft from station` : "") + `<br>`;
  if (d.shares_link_with) h += `<span class="meta">Shares this link with station ${esc(d.shares_link_with)}</span><br>`;
  if (d.detail && d.status !== "lookup_existing" && d.status !== "good_match") h += `${esc(d.detail)}<br>`;
  if (d.hwycovid == null && d.nearest_link_id != null) h += `<span class="meta">That link is highlighted on the map.</span><br>`;
  h += `2025 daily count: <b>${esc(num(d.count_day))}</b> <span class="meta">(${esc(d.n_days)} days)</span>`;
  if (d.flag_low_n_days) h += `<br><span class="meta">Fewer than 10 days of data</span>`;
  if (d.dropped_gp_under_10k) h += `<br><span class="meta">Dropped: GP link under 10,000 vehicles/day</span>`;
  return h + `</div>`;
}
ORDER.forEach(s => DATA.stations.filter(d => d.status === s).forEach(d => {
  const m = L.circleMarker([d.lat, d.lon], {pane:"stations", radius: s === "out_of_scope" ? 3.5 : 5.5,
    color:"#ffffff", weight:1, fillColor:COLORS[s], fillOpacity:.95});
  m.bindPopup(popup(d), POP());
  m.on("click", e => { L.DomEvent.stopPropagation(e); highlight(d.hwycovid ?? d.nearest_link_id, COLORS[s]); });
  groups[s].addLayer(m); markers[d.station] = {m, d}; counts[s]++;
}));
ORDER.forEach(s => groups[s].addTo(map));

const legend = document.getElementById("legend");
[...ORDER].reverse().forEach(s => {
  const row = document.createElement("label"); row.className = "row";
  row.innerHTML = `<input type="checkbox" checked><span class="dot" style="background:${COLORS[s]}"></span>` +
                  `<span>${LABELS[s]}</span><span class="n">${counts[s]}</span>`;
  row.querySelector("input").onchange = e => e.target.checked ? groups[s].addTo(map) : map.removeLayer(groups[s]);
  legend.appendChild(row);
});

const panel = document.getElementById("panel"), tog = document.getElementById("tog");
function setMin(min) {
  panel.classList.toggle("min", min);
  tog.setAttribute("aria-expanded", String(!min));
  tog.innerHTML = min ? "+" : "&minus;";
}
tog.onclick = () => setMin(!panel.classList.contains("min"));
setMin(window.innerWidth < 700);   // start collapsed on small screens

map.fitBounds(L.latLngBounds(DATA.stations.map(d => [d.lat, d.lon])), {padding:[30, 30]});

// ---- find ----
document.getElementById("q").addEventListener("keydown", e => {
  if (e.key !== "Enter") return;
  const v = e.target.value.trim(), msg = document.getElementById("msg");
  if (!v) { msg.textContent = ""; return; }
  let hit = markers[v];
  if (!hit) { const d = DATA.stations.find(x => String(x.hwycovid) === v); if (d) hit = markers[d.station]; }
  if (!hit) { msg.textContent = "No station or link " + v + " in this map."; return; }
  msg.textContent = "";
  if (!map.hasLayer(groups[hit.d.status])) groups[hit.d.status].addTo(map);
  map.setView([hit.d.lat, hit.d.lon], Math.max(map.getZoom(), 15));
  hit.m.openPopup(); highlight(hit.d.hwycovid ?? hit.d.nearest_link_id, COLORS[hit.d.status]);
});
</script>
</body>
</html>
""".replace("__DATA__", json.dumps(data, separators=(",", ":"), allow_nan=False))

OUT.write_text(html, encoding="utf-8")
print(f"{len(stations)} stations, {len(links)} links -> {OUT} ({OUT.stat().st_size / 1e3:.0f} KB)")
print(st["status"].value_counts().to_dict())
