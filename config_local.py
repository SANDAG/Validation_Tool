# config_local.py

import pandas as pd
import json

def load_data():
    df1 = pd.read_excel("data/vis_worksheet.xlsx", sheet_name='fwy_worksheet')
    df2 = pd.read_excel("data/vis_worksheet.xlsx", sheet_name='allclass_worksheet')

    with open("data/Joined_hwy_all.geojson", "r") as f:
        geojson_data = json.load(f)

    return {
        "df1": df1,
        "df2": df2,
        "geojson_data": geojson_data
    }
