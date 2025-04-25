import pandas as pd
import numpy as np
from functools import lru_cache
from databricks.sql import connect
from databricks.sdk.core import Config
import geopandas as gpd
from shapely import wkt
import json

cfg = Config()

@lru_cache(maxsize=1)
def get_connection(http_path):
    return connect(
        server_hostname=cfg.host,
        http_path=http_path,
        credentials_provider=lambda: cfg.authenticate,
    )

def read_volumes(volume_name, conn):
    with conn.cursor() as cursor:
        query = f"SELECT * FROM csv.`{volume_name}` WITH ('header' = 'true')"
        cursor.execute(query)
        return cursor.fetchall_arrow().to_pandas()

def read_table(table_name, conn):
    with conn.cursor() as cursor:
        query = f"SELECT scenario_id,ID,Length,geometry as Shape FROM {table_name} WHERE scenario_id = 261"
        cursor.execute(query)
        return cursor.fetchall_arrow().to_pandas()


# Read data
http_path_input = "/sql/1.0/warehouses/41cbd7de44cc187c"
conn = get_connection(http_path_input)

df1 = read_volumes('/Volumes/tam_v0/abm_15_2_0/validation/vis_worksheet - fwy_worksheet.csv', conn)
df2 = read_volumes('/Volumes/tam_v0/abm_15_2_0/validation/vis_worksheet - allclass_worksheet.csv', conn)
df_filtered1 = df1.dropna(subset=['count_day', 'DAY_Flow'])
df_filtered2 = df2.dropna(subset=['count_day', 'DAY_Flow'])

# Clean and Turn data to numeric data
def clean_and_convert_columns(df, columns):
    # Only keep columns that exist in the dataframe
    existing_cols = [col for col in columns if col in df.columns]
    missing_cols = [col for col in columns if col not in df.columns]

    if missing_cols:
        print(f"⚠️ Skipped missing columns: {missing_cols}")

    # Drop rows with NaN in any of the existing columns
    df_cleaned = df.dropna(subset=existing_cols).copy()

    # Convert to numeric for existing columns
    for col in existing_cols:
        df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce')

    return df_cleaned

columns_to_clean = [
    'count_day', 'count_ea', 'count_am', 'count_md', 'count_pm', 'count_ev',
    'EA_Flow', 'EA_Speed', 'EA_Vmt', 'AM_Flow', 'AM_Speed', 'AM_Vmt',
    'MD_Flow', 'MD_Speed', 'MD_Vmt', 'PM_Flow', 'PM_Speed', 'PM_Vmt',
    'EV_Flow', 'EV_Speed', 'EV_Vmt', 'DAY_Flow', 'DAY_Speed', 'DAY_Vmt',
    'TruckFlow', 'lhdTruckFlow', 'mhdTruckFlow', 'hhdTruckFlow',
    'vis_order', 'vmt_day', 'gap_day', 'vmt_gap_day',
    'vmt_ea', 'gap_ea', 'vmt_gap_ea', 'vmt_am', 'gap_am', 'vmt_gap_am',
    'vmt_md', 'gap_md', 'vmt_gap_md', 'vmt_pm', 'gap_pm', 'vmt_gap_pm',
    'vmt_ev', 'gap_ev', 'vmt_gap_ev', 'DAY_Vmt', 'vmt_day'
]

df_filtered1 = clean_and_convert_columns(df_filtered1, columns_to_clean)
df_filtered2 = clean_and_convert_columns(df_filtered2, columns_to_clean)

# Read geometry data
df_link = read_table('tam_v0.abm_15_2_0.network__emme_hwy_tcad ', conn)
df_link['geometry'] = df_link['Shape'].apply(wkt.loads)

df_filtered1['hwycovid'] = df_filtered1['hwycovid'].astype(str)
df_link['ID'] = df_link['ID'].astype(str)
merged = df_filtered1.merge(df_link, left_on='hwycovid', right_on='ID', how='left')
merged = gpd.GeoDataFrame(merged, geometry='geometry', crs='EPSG:4326')
geojson_str = merged.to_json()
geojson_data = json.loads(geojson_str)
geojson_data.head()