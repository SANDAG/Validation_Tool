# config_local
import pandas as pd
import json
from shapely import wkt
import geopandas as gpd

def load_data():
    df1 = pd.read_excel(r"T:\STORAGE-63T\2025RP_draft\abm_runs_v2\2022_S0_v2\analysis\validation\vis_worksheet.xlsx", sheet_name='fwy_worksheet')
    df2 = pd.read_excel(r"T:\STORAGE-63T\2025RP_draft\abm_runs_v2\2022_S0_v2\analysis\validation\vis_worksheet.xlsx", sheet_name='allclass_worksheet')
    df3 = pd.read_excel(r"T:\STORAGE-63T\2025RP_draft\abm_runs_v2\2022_S0_v2\analysis\validation\vis_worksheet.xlsx", sheet_name='truck_worksheet')
    df4 = pd.read_excel(r"T:\STORAGE-63T\2025RP_draft\abm_runs_v2\2022_S0_v2\analysis\validation\vis_worksheet.xlsx", sheet_name='board_worksheet')
    df_link = pd.read_csv(r"T:\STORAGE-63T\2025RP_draft\abm_runs_v2\2022_S0_v2\report\hwyTcad.csv",dtype={7: str, 8: str})
    df_route = pd.read_csv(r"T:\STORAGE-63T\2025RP_draft\abm_runs_v2\2022_S0_v2\report\transitRoute.csv")
    df_scenario = pd.DataFrame({'scenario_id': [1150], 'scenario_name': ['2022_S0_v2'], 'scenario_yr': [2022]})

    df1['label'] = df1['fxnm'].fillna('Unknown') + ' to ' + df1['txnm'].fillna('Unknown')
    df4['transit_gap_day'] = df4['gap_day']
    
    df1.columns = df1.columns.str.lower()
    df2.columns = df2.columns.str.lower()
    df3.columns = df3.columns.str.lower()
    df4.columns = df4.columns.str.lower()
    df_link.columns = df_link.columns.str.lower()
    df_route.columns = df_route.columns.str.lower()

    df1['scenario_id']=1150
    df2['scenario_id']=1150
    df3['scenario_id']=1150
    df4['scenario_id']=1150

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

    return {
        "df1": df1,
        "df2": df2,
        "df3": df3,
        "df4": df4,
        "geojson_data": geojson_data,
        "geojson_data_r":geojson_data_r,
        "df_scenario":df_scenario
    }