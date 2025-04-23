import pandas as pd
import numpy as np
from dash import Dash, dcc, html, dash_table, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import dash_leaflet as dl
from functools import lru_cache
from databricks import sql
from databricks.sdk.core import Config
import geopandas as gpd

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

def read_table(table_name, conn):
    with conn.cursor() as cursor:
        query = f"SELECT scenario_id,ID,Length,FC,FFC, SPHERE,geometry as Shape FROM {table_name} WHERE scenario_id = 1132"
        cursor.execute(query)
        return cursor.fetchall_arrow().to_pandas()


# Read data
http_path_input = "/sql/1.0/warehouses/41cbd7de44cc187c"
conn = get_connection(http_path_input)

df = read_volumes('/Volumes/tam/abm_15_2_0/validation/vis_worksheet - fwy_worksheet.csv', conn)
df2 = read_volumes('/Volumes/tam/abm_15_2_0/validation/vis_worksheet - gap_stat_road_type.csv', conn)
df3 = read_table('tam.abm_15_2_0.network__emme_hwy_tcad ', conn)

print(df3.head())
# geo_path = "/dbfs/Volumes/tam/abm_15_2_0/validation/Joined_hwy.geojson"
# geojson_data = read_geojson_fallback('/Volumes/tam/abm_15_2_0/validation/Joined_hwy.geojson')
# print(geojson_data.head())
df_filtered = df.dropna(subset=['count_day', 'DAY_Flow'])

# R2 and slope per PMSA
results = []
for pmsa, group in df_filtered.groupby('pmsa_nm'):
    x = pd.to_numeric(group['count_day'], errors='coerce')
    y = pd.to_numeric(group['DAY_Flow'], errors='coerce')
    mask = ~np.isnan(x) & ~np.isnan(y)
    x_clean = x[mask]
    y_clean = y[mask]
    if len(x_clean) > 1:
        slope, intercept = np.polyfit(x_clean, y_clean, 1)
        y_pred = slope * x_clean + intercept
        r_squared = 1 - np.sum((y_clean - y_pred) ** 2) / np.sum((y_clean - y_clean.mean()) ** 2)
        results.append({'PMSA': pmsa, 'R_squared': round(r_squared, 2), 'Slope': round(slope, 2)})
r2slope_df = pd.DataFrame(results)

# Bar chart
bar_fig = px.bar(
    r2slope_df.melt(id_vars='PMSA', value_vars=['R_squared', 'Slope']),
    x='PMSA',
    y='value',
    color='variable',
    barmode='group',
    labels={'value': 'Metric Value', 'variable': 'Metric'},
    color_discrete_map={'R_squared': '#08306b', 'Slope': '#cb181d'}
)

# Scatter chart
scatter_fig = px.scatter(df_filtered, x='count_day', y='DAY_Flow', title='Observed vs Modeled Day Flow')

# Dropdown for histogram
gap_dropdown = dcc.Dropdown(
    id='gap_metric_dropdown',
    options=[{'label': col, 'value': col} for col in df2.columns if col != 'Class'],
    value=df2.columns[0],
    clearable=False,
    style={'marginBottom': '10px'}
)

# Map placeholder
leaflet_map = dl.Map(center=[32.7157, -117.1611], zoom=8, children=[
    dl.TileLayer(),
    dl.Marker(position=[32.7157, -117.1611], children=dl.Popup("Sample Location"))
], style={'height': '380px', 'width': '100%'})

# Dash app
dash_app = Dash(__name__)

dash_app.layout = html.Div([
    html.H1("Dash Demo: SANDAG ABM Validation Project Dashboard"),
    html.P("This dashboard provides a preview of table, scatter chart, bar chart and web map."),

    html.Div([
        # Left column
        html.Div([
            html.Div([
                html.H2("Gap Statistic by Road Type"),
                dash_table.DataTable(
                    data=df2.drop(columns=['Class']).to_dict('records'),
                    columns=[{"name": col, "id": col} for col in df2.columns if col != 'Class'],
                    style_table={'overflowX': 'auto', 'height': '300px'},
                    page_size=10,
                    style_cell={'textAlign': 'left', 'padding': '5px'},
                    style_header={'fontWeight': 'bold'}
                )
            ], style={'flex': '1', 'marginBottom': '20px'}),

            html.Div([
                html.H2("Gap Metric Histogram"),
                gap_dropdown,
                dcc.Graph(id='gap_histogram', style={'height': '380px'})
            ], style={'flex': '1'})
        ], style={'flex': 1, 'display': 'flex', 'flexDirection': 'column', 'padding': '10px'}),

        # Middle column
        html.Div([
            html.Div([
                html.H2("R² and Slope by PMSA"),
                dcc.Graph(figure=bar_fig, style={'height': '380px'})
            ], style={'marginBottom': '20px'}),

            html.Div([
                html.H2("Model Day Flow VS Observed Daily Count"),
                dcc.Graph(id='scatter', figure=scatter_fig, style={'height': '380px'})
            ])
        ], style={'flex': 1, 'display': 'flex', 'flexDirection': 'column', 'padding': '10px'}),

        # Right column
        html.Div([
            html.H2("Map: Gap Day by Hwy Coverage ID"),
            leaflet_map
        ], style={'width': '40%', 'display': 'flex', 'flexDirection': 'column', 'padding': '10px'})
    ], style={'display': 'flex', 'flexDirection': 'row', 'height': '700px'})
])

# Histogram callback
@dash_app.callback(
    Output('gap_histogram', 'figure'),
    Input('gap_metric_dropdown', 'value')
)
def update_histogram(selected_metric):
    if selected_metric and selected_metric in df2.columns:
        return px.histogram(df2, x=selected_metric, nbins=30, title=f"Histogram of {selected_metric}")
    return go.Figure()

# Run app
if __name__ == '__main__':
    dash_app.run_server(debug=True)
