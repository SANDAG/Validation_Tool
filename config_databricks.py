# config_databricks.py

import pandas as pd
import numpy as np
import geopandas as gpd
from shapely import wkt
import json
from functools import lru_cache
from databricks import sql
from databricks.sdk.core import Config

# === Connection setup ===
cfg = Config()

@lru_cache(maxsize=1)
def get_connection(http_path):
    return sql.connect(
        server_hostname=cfg.host,
        http_path=http_path,
        credentials_provider=lambda: cfg.authenticate,
    )

# def read_volumes(volume_name, conn):
#     with conn.cursor() as cursor:
#         query = f"SELECT * FROM csv.`{volume_name}` WITH ('header' = 'true')"
#         cursor.execute(query)
#         return cursor.fetchall_arrow().to_pandas()

def read_geotable(table_name, conn):
    with conn.cursor() as cursor:
        query = f"SELECT scenario_id, ID, Length, geometry as Shape FROM {table_name} WHERE scenario_id = 261"
        cursor.execute(query)
        return cursor.fetchall_arrow().to_pandas()

def read_table(table_name, conn):
    with conn.cursor() as cursor:
        query = f"SELECT * FROM {table_name}"
        cursor.execute(query)
        return cursor.fetchall_arrow().to_pandas()

# === Utility ===
def clean_and_convert_columns(df, columns):
    existing_cols = [col for col in columns if col in df.columns]
    df_cleaned = df.dropna(subset=existing_cols).copy()
    for col in existing_cols:
        df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce')
    return df_cleaned

# === Main function ===
def load_data():
    http_path_input = "/sql/1.0/warehouses/41cbd7de44cc187c"
    conn = get_connection(http_path_input)

    df1 = read_table('tam_dev.validation.fwy', conn)
    df2 = read_table('tam_dev.validation.all_calss', conn)

    df_filtered1 = df1.dropna(subset=['count_day', 'DAY_Flow'])
    df_filtered1['Label'] = df_filtered1['fxnm'].fillna('Unknown') + ' to ' + df_filtered1['txnm'].fillna('Unknown')
    df_filtered2 = df2.dropna(subset=['count_day', 'DAY_Flow'])

    columns_to_clean = [
        'count_day', 'count_ea', 'count_am', 'count_md', 'count_pm', 'count_ev',
        'EA_Flow', 'EA_Speed', 'EA_Vmt', 'AM_Flow', 'AM_Speed', 'AM_Vmt',
        'MD_Flow', 'MD_Speed', 'MD_Vmt', 'PM_Flow', 'PM_Speed', 'PM_Vmt',
        'EV_Flow', 'EV_Speed', 'EV_Vmt', 'DAY_Flow', 'DAY_Speed', 'DAY_Vmt',
        'TruckFlow', 'lhdTruckFlow', 'mhdTruckFlow', 'hhdTruckFlow',
        'vis_order', 'vmt_day', 'gap_day', 'vmt_gap_day',
        'vmt_ea', 'gap_ea', 'vmt_gap_ea', 'vmt_am', 'gap_am', 'vmt_gap_am',
        'vmt_md', 'gap_md', 'vmt_gap_md', 'vmt_pm', 'gap_pm', 'vmt_gap_pm',
        'vmt_ev', 'gap_ev', 'vmt_gap_ev', 'DAY_Vmt', 'vmt_day',
        'length','speed_day','speed_ea','speed_am','speed_md','speed_pm','speed_ev'
    ]

    df_filtered1 = clean_and_convert_columns(df_filtered1, columns_to_clean)
    df_filtered2 = clean_and_convert_columns(df_filtered2, columns_to_clean)

    df_link = read_geotable('tam.abm_15_2_0.network__emme_hwy_tcad ', conn)
    df_link['geometry'] = df_link['Shape'].apply(wkt.loads)

    df_filtered1['hwycovid'] = df_filtered1['hwycovid'].astype(str)
    df_link['ID'] = df_link['ID'].astype(str)
    merged = df_filtered2.merge(df_link, left_on='hwycovid', right_on='ID', how='left')

    merged = gpd.GeoDataFrame(merged, geometry='geometry', crs='EPSG:2230')
    merged = merged.to_crs('EPSG:4326')
    geojson_str = merged.to_json()
    geojson_data = json.loads(geojson_str)

    return {
        "df1": df_filtered1,
        "df2": df_filtered2,
        "geojson_data": geojson_data
    }
