import pandas as pd
import json
from shapely import wkt
import geopandas as gpd
import os
import yaml
from pathlib import Path
from databricks import sql

# Identify Environment
if os.getenv("LOCAL_FLAG") == "0":
    ENV = "Azure"
else:
    ENV = "local"

print(f"✅ Running in environment: {ENV}")

if ENV == "local":
    raw_paths = os.getenv("LOCAL_SCENARIO_LIST", "")
    scenario_dirs = [p.strip() for p in raw_paths.split(',') if p.strip()]

    def read_metadata(scenario_path):
        meta_path = Path(scenario_path) / "output" / "datalake_metadata.yaml"
        if not meta_path.exists():
            folder_name = Path(scenario_path).name
            print(f"⚠️ Metadata file missing in {scenario_path}, assigning default scenario_id=999 and name='{folder_name}'")
            return {
                "scenario_id": 999,
                "scenario_name": folder_name,
                "scenario_yr": 0
            }
        with open(meta_path, "r") as f:
            meta = yaml.safe_load(f)
        return {
            "scenario_id": int(meta.get("scenario_id")),
            "scenario_name": meta.get("scenario_title"),
            "scenario_yr": int(meta.get("scenario_year"))
        }

    dfs = {
        "df1": [],
        "df2": [],
        "df3": [],
        "df4": [],
        "df_scenario": []
    }

    df_link = None
    df_route = None

    for i, scenario_path in enumerate(scenario_dirs):
        meta = read_metadata(scenario_path)

        try:
            dfs["df1"].append(pd.read_csv(f"{scenario_path}\\analysis\\validation\\vis_worksheet - fwy_worksheet.csv").assign(scenario_id=meta["scenario_id"]))
            dfs["df2"].append(pd.read_csv(f"{scenario_path}\\analysis\\validation\\vis_worksheet - allclass_worksheet.csv").assign(scenario_id=meta["scenario_id"]))
            dfs["df3"].append(pd.read_csv(f"{scenario_path}\\analysis\\validation\\vis_worksheet - truck_worksheet.csv").assign(scenario_id=meta["scenario_id"]))
            dfs["df4"].append(pd.read_csv(f"{scenario_path}\\analysis\\validation\\vis_worksheet - board_worksheet.csv").assign(scenario_id=meta["scenario_id"]))
            dfs["df_scenario"].append(pd.DataFrame([meta]))

            # Only load df_link and df_route once from the first scenario
            if i == 0:
                df_link = pd.read_csv(f"{scenario_path}\\report\\hwyTcad.csv", dtype={7: str, 8: str}).assign(scenario_id=meta["scenario_id"])
                df_route = pd.read_csv(f"{scenario_path}\\report\\transitRoute.csv").assign(scenario_id=meta["scenario_id"])

        except FileNotFoundError as e:
            print(f"⚠️ Missing file in {scenario_path}: {e}")

    # Concatenate all scenario data
    df1 = pd.concat(dfs["df1"], ignore_index=True)
    df2 = pd.concat(dfs["df2"], ignore_index=True)
    df3 = pd.concat(dfs["df3"], ignore_index=True)
    df4 = pd.concat(dfs["df4"], ignore_index=True)
    df_scenario = pd.concat(dfs["df_scenario"], ignore_index=True)

elif ENV == 'Azure':
    raw_ids = os.getenv("AZURE_SCENARIO_LIST", "")
    scenario_id_list = [int(s.strip()) for s in raw_ids.split(',') if s.strip().isdigit()]
    scenario_str = ','.join(map(str, scenario_id_list))
    default_scenario = 1150

    def query_to_df(cursor, query):
        cursor.execute(query)
        return cursor.fetchall_arrow().to_pandas()

    with sql.connect(
        server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
        http_path=os.getenv("DATABRICKS_HTTP_PATH"),
        access_token=os.getenv("DATABRICKS_TOKEN")
    ) as connection:
        with connection.cursor() as cursor:
            df1 = query_to_df(cursor, f"SELECT * FROM tam_dev.validation.fwy WHERE scenario_id IN ({scenario_str})")
            df2 = query_to_df(cursor, f"SELECT * FROM tam_dev.validation.all_class WHERE scenario_id IN ({scenario_str})")
            df3 = query_to_df(cursor, f"SELECT * FROM tam_dev.validation.truck WHERE scenario_id IN ({scenario_str})")
            df4 = query_to_df(cursor, f"SELECT * FROM tam_dev.validation.board WHERE scenario_id IN ({scenario_str})")
            df_link = query_to_df(cursor, f"SELECT scenario_id, ID, Length, geometry FROM tam_dev.abm3.network__emme_hwy_tcad WHERE scenario_id = {default_scenario}")
            df_route = query_to_df(cursor, f"SELECT scenario_id, route_name, earlyam_hours, evening_hours, transit_route_shape as geometry FROM tam_dev.abm3.network__transit_route WHERE scenario_id = {default_scenario}")
            df_scenario = query_to_df(cursor, f"SELECT scenario_id, scenario_name, scenario_yr FROM tam_dev.abm3.main__scenario WHERE scenario_id IN ({scenario_str})")

    # Clean up data
    df1 = df1.dropna(subset=['count_day', 'day_flow']).drop(columns=['loader__delta_hash_key','loader__updated_date'], errors='ignore').drop_duplicates()
    df2 = df2.dropna(subset=['count_day', 'day_flow']).drop(columns=['loader__delta_hash_key','loader__updated_date'], errors='ignore').drop_duplicates()
    df3 = df3.drop(columns=['loader__delta_hash_key','loader__updated_date'], errors='ignore').drop_duplicates()
    df4 = df4.drop(columns=['loader__delta_hash_key','loader__updated_date'], errors='ignore').drop_duplicates()

# add label column
df1['label'] = df1['fxnm'].fillna('Unknown') + ' to ' + df1['txnm'].fillna('Unknown')
df4['transit_gap_day'] = df4['gap_day']
# Lowercase column names
for df in [df1, df2, df3, df4, df_link, df_route]:
    df.columns = df.columns.str.lower()

# Processing Geojson files
# Processsing merged files to inculde all links from all_class and truck
df2_subset = df2[['hwycovid', 'gap_day', 'vmt_gap_day']].rename(
columns={'gap_day': 'gap_day_all_class','vmt_gap_day': 'vmt_gap_day_all_class'})
df3_subset = df3[['hwycovid', 'gap_day', 'vmt_gap_day']].rename(
    columns={'gap_day': 'gap_day_truck','vmt_gap_day': 'vmt_gap_day_truck'})

# Merge the two DataFrames on hwycovid using an outer join
merged_df = pd.merge(df2_subset, df3_subset, on='hwycovid', how='outer')
merged_df['hwycovid_str'] = merged_df['hwycovid'].astype(str)
merged_df['gap_day'] = merged_df['gap_day_all_class'].combine_first(merged_df['gap_day_truck'])
df_link['geometry'] = df_link['geometry'].apply(wkt.loads)
df_link['id'] = df_link['id'].astype(str)
merged = merged_df.merge(df_link, left_on='hwycovid_str', right_on='id', how='left')

merged = gpd.GeoDataFrame(merged, geometry='geometry', crs='EPSG:2230')
merged = merged.to_crs('EPSG:4326')
geojson_str = merged.to_json()
geojson_data = json.loads(geojson_str)

df_route['geometry'] = df_route['geometry'].apply(wkt.loads)
df_route['route_name_id'] = df_route['route_name'].astype(str).str[:-3]
df4['route_str'] = df4['route'].astype(str)
merged_route = df4.merge(df_route,left_on='route_str',right_on='route_name_id',how='left')
merged_route = gpd.GeoDataFrame(merged_route, geometry='geometry', crs='EPSG:2230')
merged_route = merged_route.to_crs('EPSG:4326')
geojson_str_r = merged_route.to_json()
geojson_data_r = json.loads(geojson_str_r)

def load_data():

    return {
        "df1": df1,
        "df2": df2,
        "df3": df3,
        "df4": df4,
        "geojson_data": geojson_data,
        "geojson_data_r":geojson_data_r,
        "df_scenario":df_scenario
    }