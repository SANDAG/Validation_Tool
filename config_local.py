# config_local.py

import pandas as pd
import json

def load_data():
    df1 = pd.read_excel(r"T:\STORAGE-63T\2025RP_draft\abm_runs_v2\2022_S0_v2\analysis\validation\vis_worksheet.xlsx", sheet_name='fwy_worksheet')
    df2 = pd.read_excel(r"T:\STORAGE-63T\2025RP_draft\abm_runs_v2\2022_S0_v2\analysis\validation\vis_worksheet.xlsx", sheet_name='allclass_worksheet')
    df3 = pd.read_excel(r"T:\STORAGE-63T\2025RP_draft\abm_runs_v2\2022_S0_v2\analysis\validation\vis_worksheet.xlsx", sheet_name='truck_worksheet')
    df4 = pd.read_excel(r"T:\STORAGE-63T\2025RP_draft\abm_runs_v2\2022_S0_v2\analysis\validation\vis_worksheet.xlsx", sheet_name='board_worksheet')

    with open(r"T:\STORAGE-63T\2025RP_draft\abm_runs_v2\2022_S0_v2\analysis\validation\Joined_hwy_all.geojson", "r") as f:
        geojson_data = json.load(f)
    
    df1['label'] = df1['fxnm'].fillna('Unknown') + ' to ' + df1['txnm'].fillna('Unknown')
    
    df1.columns = df1.columns.str.lower()
    df2.columns = df2.columns.str.lower()
    df3.columns = df3.columns.str.lower()
    df4.columns = df4.columns.str.lower()

    return {
        "df1": df1,
        "df2": df2,
        "df3": df3,
        "df4": df4,
        "geojson_data": geojson_data
    }
