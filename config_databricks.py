# config_databricks.py
import os
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

def read_volumes(volume_name, conn):
    with conn.cursor() as cursor:
        query = f"SELECT * FROM csv.`{volume_name}` WITH ('header' = 'true')"
        cursor.execute(query)
        return cursor.fetchall_arrow().to_pandas()

def read_geotable(table_name, conn):
    with conn.cursor() as cursor:
        query = f"SELECT scenario_id, ID, Length, geometry as Shape FROM {table_name} WHERE scenario_id = 1150"
        cursor.execute(query)
        return cursor.fetchall_arrow().to_pandas()

def read_table(table_name, conn, scenario_id):
    with conn.cursor() as cursor:
        query = f"SELECT * FROM {table_name} WHERE scenario_id = {scenario_id}"
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
    SCENARIO_ID = int(os.getenv("SCENARIO_ID", "1150"))
    print(f"🔍 Using SCENARIO_ID: {SCENARIO_ID}") 
    http_path_input = "/sql/1.0/warehouses/41cbd7de44cc187c"
    conn = get_connection(http_path_input)

    df1 = read_table('tam_dev.validation.fwy', conn,SCENARIO_ID)
    df2 = read_table('tam_dev.validation.all_class', conn,SCENARIO_ID)

    df_filtered1 = df1.dropna(subset=['count_day', 'day_flow']).drop(columns=['loader__delta_hash_key','loader__updated_date'])
    df_filtered1['Label'] = df_filtered1['fxnm'].fillna('Unknown') + ' to ' + df_filtered1['txnm'].fillna('Unknown')
    df_filtered2 = df2.dropna(subset=['count_day', 'day_flow']).drop(columns=['loader__delta_hash_key','loader__updated_date'])

    columns_to_clean = [
        'count_day', 'count_ea', 'count_am', 'count_md', 'count_pm', 'count_ev',
        'ea_flow', 'ea_speed', 'ea_vmt', 'am_flow', 'am_speed', 'am_vmt',
        'md_flow', 'md_speed', 'md_vmt', 'pm_flow', 'pm_speed', 'pm_vmt',
        'ev_flow', 'ev_speed', 'ev_vmt', 'day_flow', 'day_speed', 'day_vmt',
        'truckflow', 'lhdtruckflow', 'mhdtruckflow', 'hhdtruckflow',
        'vis_order', 'vmt_day', 'gap_day', 'vmt_gap_day',
        'vmt_ea', 'gap_ea', 'vmt_gap_ea', 'vmt_am', 'gap_am', 'vmt_gap_am',
        'vmt_md', 'gap_md', 'vmt_gap_md', 'vmt_pm', 'gap_pm', 'vmt_gap_pm',
        'vmt_ev', 'gap_ev', 'vmt_gap_ev', 'day_vmt', 'vmt_day',
        'length', 'speed_day', 'speed_ea', 'speed_am', 'speed_md', 'speed_pm', 'speed_ev'
    ]

    df_filtered1 = clean_and_convert_columns(df_filtered1, columns_to_clean)
    df_filtered2 = clean_and_convert_columns(df_filtered2, columns_to_clean)

    df_link = read_geotable('tam_dev.abm3.network__emme_hwy_tcad ', conn)
    df_link['geometry'] = df_link['Shape'].apply(wkt.loads)

    df_filtered2['hwycovid_str'] = df_filtered2['hwycovid'].astype(str)
    df_link['ID'] = df_link['ID'].astype(str)
    merged = df_filtered2.merge(df_link, left_on='hwycovid_str', right_on='ID', how='left')

    merged = gpd.GeoDataFrame(merged, geometry='geometry', crs='EPSG:2230')
    merged = merged.to_crs('EPSG:4326')
    geojson_str = merged.to_json()
    geojson_data = json.loads(geojson_str)

    return {
        "df1": df_filtered1,
        "df2": df_filtered2,
        "geojson_data": geojson_data
    }
