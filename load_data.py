from databricks-sql-connector import sql
import os
import pandas as pd
import geopandas as gpd
import json
from shapely import wkt
from dotenv import load_dotenv, find_dotenv

# Only load if the .env file is present
dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path)

scenario_id_list = [1150,272,254]
scenario_str = ','.join(map(str, scenario_id_list))

def load_data():
    with sql.connect(server_hostname = os.getenv("DATABRICKS_SERVER_HOSTNAME"),
                    http_path       = os.getenv("DATABRICKS_HTTP_PATH"),
                    access_token    = os.getenv("DATABRICKS_TOKEN")) as connection:
        
        df1 = pd.read_sql(f'SELECT * FROM tam_dev.validation.fwy WHERE scenario_id IN ({scenario_str})',connection)
        df2 = pd.read_sql(f'SELECT * FROM tam_dev.validation.all_class WHERE scenario_id IN ({scenario_str})',connection)
        df3 = pd.read_sql(f'SELECT * FROM tam_dev.validation.truck WHERE scenario_id IN ({scenario_str})',connection)
        df4 = pd.read_sql(f'SELECT * FROM tam_dev.validation.board WHERE scenario_id IN ({scenario_str})',connection)
        df_link = pd.read_sql(f'SELECT scenario_id, ID, Length, geometry as Shape FROM tam_dev.abm3.network__emme_hwy_tcad WHERE scenario_id is 1150',connection)


    df_filtered1 = df1.dropna(subset=['count_day', 'day_flow']).drop(columns=['loader__delta_hash_key','loader__updated_date']).drop_duplicates()
    df_filtered1['label'] = df_filtered1['fxnm'].fillna('Unknown') + ' to ' + df_filtered1['txnm'].fillna('Unknown')
    df_filtered2 = df2.dropna(subset=['count_day', 'day_flow']).drop(columns=['loader__delta_hash_key','loader__updated_date']).drop_duplicates()
    df_filtered3 = df3.drop(columns=['loader__delta_hash_key','loader__updated_date']).drop_duplicates()
    df_filtered4 = df4.drop(columns=['loader__delta_hash_key','loader__updated_date']).drop_duplicates()

    columns_to_clean = [
        'count_day', 'count_ea', 'count_am', 'count_md', 'count_pm', 'count_ev',
        'ea_flow', 'ea_speed', 'ea_vmt', 'am_flow', 'am_speed', 'am_vmt',
        'md_flow', 'md_speed', 'md_vmt', 'pm_flow', 'pm_speed', 'pm_vmt',
        'ev_flow', 'ev_speed', 'ev_vmt', 'day_flow', 'day_speed', 'day_vmt',
        'truckflow', 'lhdtruckflow', 'mhdtruckflow', 'hhdtruckflow',
        'truckaadt','lhdtruckaadt','mhdtruckaadt','hhdtruckaadt',
        'vis_order', 'vmt_day', 'gap_day', 'vmt_gap_day',
        'vmt_ea', 'gap_ea', 'vmt_gap_ea', 'vmt_am', 'gap_am', 'vmt_gap_am',
        'vmt_md', 'gap_md', 'vmt_gap_md', 'vmt_pm', 'gap_pm', 'vmt_gap_pm',
        'vmt_ev', 'gap_ev', 'vmt_gap_ev', 'day_vmt', 'vmt_day',
        'length', 'speed_day', 'speed_ea', 'speed_am', 'speed_md', 'speed_pm', 'speed_ev'
    ]

    def clean_and_convert_columns(df, columns):
        existing_cols = [col for col in columns if col in df.columns]
        df_cleaned = df.dropna(subset=existing_cols).copy()
        for col in existing_cols:
            df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce')
        return df_cleaned

    df_filtered1 = clean_and_convert_columns(df_filtered1, columns_to_clean)
    df_filtered2 = clean_and_convert_columns(df_filtered2, columns_to_clean)
    df_filtered3 = clean_and_convert_columns(df_filtered3, columns_to_clean)
    df_filtered4 = clean_and_convert_columns(df_filtered4, columns_to_clean)


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
        "df3": df_filtered3,
        "df4": df_filtered4,
        "geojson_data": geojson_data
    }
