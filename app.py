import pandas as pd
import numpy as np
import dash
from dash import Dash, dcc, html, dash_table, Input, Output, State, callback_context
import plotly.express as px
import plotly.graph_objects as go
import dash_leaflet as dl
from functools import lru_cache
from databricks import sql
from databricks.sdk.core import Config
from dash_extensions.javascript import assign
import geopandas as gpd
from shapely import wkt
import json

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
        query = f"SELECT scenario_id,ID,Length,geometry as Shape FROM {table_name} WHERE scenario_id = 261"
        cursor.execute(query)
        return cursor.fetchall_arrow().to_pandas()


# Read data
http_path_input = "/sql/1.0/warehouses/41cbd7de44cc187c"
conn = get_connection(http_path_input)

df = read_volumes('/Volumes/tam_v0/abm_15_2_0/validation/vis_worksheet - fwy_worksheet.csv', conn)
df2 = read_volumes('/Volumes/tam_v0/abm_15_2_0/validation/vis_worksheet - gap_stat_road_type.csv', conn)
df_filtered = df.dropna(subset=['count_day', 'DAY_Flow'])

# Read geometry data
df_link = read_table('tam_v0.abm_15_2_0.network__emme_hwy_tcad ', conn)
df_link['geometry'] = df_link['Shape'].apply(wkt.loads)

df['hwycovid'] = df['hwycovid'].astype(str)
df_link['ID'] = df_link['ID'].astype(str)
merged = df.merge(df_link, left_on='hwycovid', right_on='ID', how='left')
merged = gpd.GeoDataFrame(merged, geometry='geometry', crs='EPSG:4326')
geojson_str = merged.to_json()
geojson_data = json.loads(geojson_str)

# === Create line plot: hwycovid (label) vs count_day and DAY_Flow ===
line_df = df_filtered.copy()
line_df['Label'] = line_df['fxnm'].fillna('Unknown') + ' to ' + line_df['txnm'].fillna('Unknown')

# Sort by hwycovid to ensure consistent ordering
line_df = line_df.sort_values(by='hwycovid')

line_fig = go.Figure()

line_fig.add_trace(go.Scatter(
    x=line_df['hwycovid'],
    y=line_df['DAY_Flow'],
    customdata=line_df[['hwycovid']],
    mode='lines+markers',
    name='Model DAY_Flow',
    line=dict(color='#08306b')
))

line_fig.add_trace(go.Scatter(
    x=line_df['hwycovid'],
    y=line_df['count_day'],
    customdata=line_df[['hwycovid']],
    mode='lines+markers',
    name='Observed count_day',
    line=dict(color='#cb181d')
))

line_fig.update_layout(
    xaxis_title='Highway Segment',
    yaxis_title='Volume',
    height=500,
    margin=dict(l=20, r=20, t=70, b=120),
    legend=dict(
        orientation='h',
        yanchor='bottom',
        y=1.02,
        xanchor='left',
        x=0
    ),
    xaxis=dict(
        type='category',
        tickangle=45,
        tickmode='array',
        tickvals=line_df['hwycovid'],
        ticktext=line_df['Label'],
        tickfont=dict(size=10),
        showgrid=False,
        range=[-0.9, len(line_df) - 0.9]  # 👈 eliminate extra padding
    )
)


# === Calculate R² and slope per PMSA ===
results = []

for pmsa, group in df_filtered.groupby('pmsa_nm'):
    # Convert to numeric (handle any non-numeric entries)
    x = pd.to_numeric(group['count_day'], errors='coerce')
    y = pd.to_numeric(group['DAY_Flow'], errors='coerce')
    
    # Drop rows where either x or y is NaN
    mask = ~np.isnan(x) & ~np.isnan(y)
    x_clean = x[mask]
    y_clean = y[mask]

    if len(x_clean) > 1:
        slope, intercept = np.polyfit(x_clean, y_clean, 1)
        y_pred = slope * x_clean + intercept
        r_squared = 1 - np.sum((y_clean - y_pred) ** 2) / np.sum((y_clean - y_clean.mean()) ** 2)
        results.append({
            'PMSA': pmsa,
            'R_squared': round(r_squared, 2),
            'Slope': round(slope, 2)
        })

r2slope_df = pd.DataFrame(results)



# === Scatter Plot: count_day vs DAY_Flow ===
scatter_df = df_filtered[['count_day', 'DAY_Flow','hwycovid']].dropna()
scatter_fig = px.scatter(
    scatter_df,
    x='count_day',
    y='DAY_Flow',
    custom_data=['hwycovid'],
    labels={'count_day': 'Observed Daily Count', 'DAY_Flow': 'Model Day Flow'},
    color_discrete_sequence=["#08306b"]
)

scatter_fig.update_layout(height=500, width=700)


# === Create bar graph of 'R² and slope per PMSA'
bar_fig = px.bar(
    r2slope_df.melt(id_vars='PMSA', value_vars=['R_squared', 'Slope']),
    x='PMSA',
    y='value',
    color='variable',
    barmode='group',
    labels={'value': 'Metric Value', 'variable': 'Metric'},
    color_discrete_map={'R_squared': '#08306b', 'Slope': '#cb181d'}
)

# === Create histogram of 'gap_day'
hist_fig = px.histogram(
    df_filtered.dropna(subset=['gap_day']),
    x='gap_day',
    nbins=30,
    labels={'gap_day': 'Gap Day'},
    color_discrete_sequence=["#08306b"]
)

# --- Dropdown component for selecting gap metric
gap_dropdown = html.Div([
    html.Label("Select Gap Column:"),
    dcc.Dropdown(
        id='gap_column_selector',
        options=[
            {'label': 'Gap Day', 'value': 'gap_day'},
            {'label': 'Gap EA', 'value': 'gap_ea'},
            {'label': 'Gap AM', 'value': 'gap_am'},
            {'label': 'Gap MD', 'value': 'gap_md'},
            {'label': 'Gap PM', 'value': 'gap_pm'},
            {'label': 'Gap EV', 'value': 'gap_ev'}
        ],
        value='gap_day',  # default selection
        clearable=False
    )
], style={'marginBottom': '20px'})


# === Define style function directly in JavaScript ===
# This approach avoids issues with the arrow_function
style_function = assign("""function(feature, context) {
    const props = context && context.props ? context.props : {};
    const hideout = context.hideout || {};
    const highlight_id = hideout.highlight_id;
    const isHighlighted = feature.properties.hwycovid == highlight_id;

    if (isHighlighted) {
        return { color: "yellow", weight: 6, opacity: 1.0 };
    }

    const gap = feature.properties.gap_day;
    let color = 'gray';

    if (gap !== null && gap !== undefined) {
        if (gap < -10) {
            color = '#08306b';
        } else if (gap < -5) {
            color = '#2171b5';
        } else if (gap < 0) {
            color = '#6baed6';
        } else if (gap < 5) {
            color = '#fc9272';
        } else if (gap < 10) {
            color = '#fb6a4a';
        } else {
            color = '#cb181d';
        }
    }

    if (isHighlighted) {
        return {
            color: 'yellow',
            weight: 6,
            opacity: 1.0
        };
    }

    return {
        color: color,
        weight: 3,
        opacity: 0.7
    };
}""")



# Define a simple hover style
hover_style = dict(weight=5, color='#666', dashArray='', fillOpacity=0.7)

# === Initialize Dash App ===
app = Dash(__name__)


# === Create Leaflet Map ===
leaflet_map = dl.Map(
    id='map',
    center=[32.85, -116.9],
    zoom=10,  # zoom will now work since we removed zoomToBounds
    children=[
        dl.TileLayer(
            url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
            attribution='© OpenStreetMap contributors, © CartoDB'
        ),
        dl.GeoJSON(
            data=geojson_data,
            id="geojson",
            hoverStyle=hover_style,
            hideout={"highlight_id": None, "selected": []},
            style=style_function,
            children=[
                dl.Popup(id="popup")
            ]
        ),

        # Custom HTML legend here:
        html.Div([
            html.Div([
                html.B("Gap Day Legend"),
                html.Div("Gap < -10", style={'color': '#08306b'}),
                html.Div("-10 ≤ Gap < -5", style={'color': '#2171b5'}),
                html.Div("-5 ≤ Gap < 0", style={'color': '#6baed6'}),
                html.Div("0 ≤ Gap < 5", style={'color': '#fc9272'}),
                html.Div("5 ≤ Gap < 10", style={'color': '#fb6a4a'}),
                html.Div("Gap ≥ 10", style={'color': '#cb181d'})
            ], style={
                'position': 'absolute',
                'bottom': '20px',
                'right': '20px',
                'zIndex': '1000',
                'background': 'white',
                'padding': '10px',
                'border': '1px solid #ccc',
                'borderRadius': '5px',
                'fontSize': '12px',
                'lineHeight': '1.2em',
                'boxShadow': '0px 0px 5px rgba(0,0,0,0.3)'
            })
        ])
    ],
    style={'width': '100%', 'height': '700px'}
)


# === App Layout ===
app.layout = html.Div([
    html.H1("Dash Demo: SANDAG ABM Validation Project Dashboard"),
    html.P("This dashboard provides a preview of table, scatter chart, bar chart and web map."),

    html.Div([
    html.H2("Line Chart: DAY_Flow vs count_day by Segment"),
    dcc.Graph(id='line_plot',figure=line_fig, style={'width': '6000px','height':'600px', 'overflowX': 'scroll'})
], style={
    'width': '100%',
    'overflowX': 'auto',
    'whiteSpace': 'nowrap',
    'padding': '10px'
}),

    html.Div([
        # Left column: table + histogram
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
        ], style={'flex': 1, 'display': 'flex', 'flexDirection': 'column', 'padding': '10px', 'height': '100%'}),

        # Middle column: bar + scatter
        html.Div([
            html.Div([
                html.H2("R² and Slope by PMSA"),
                dcc.Graph(figure=bar_fig, style={'height': '380px'})
            ], style={'marginBottom': '20px'}),

            html.Div([
                html.H2("Model Day Flow VS Observed Daily Count"),
                dcc.Graph(id='scatter',figure=scatter_fig, style={'height': '380px'})
            ], style={'flex': '1'})
        ], style={'flex': 1, 'display': 'flex', 'flexDirection': 'column', 'padding': '10px', 'height': '100%'}),

        # Right column: map
        html.Div([
            html.H2("Map: Gap Day by Hwy Coverage ID"),
            leaflet_map
        ], style={'width': '40%', 'display': 'flex', 'flexDirection': 'column', 'padding': '10px', 'height': '120%'})
    ], style={
        'display': 'flex',
        'flexDirection': 'row',
        'alignItems': 'stretch',
        'height': '700px'
    })
], style={'fontFamily': 'Open Sans, verdana, arial, sans-serif'})



@app.callback(
    Output("popup", "children"),
    Input("geojson", "clickData")
)
def show_popup(clickData):
    
    if not clickData or "properties" not in clickData:
        return "No feature selected"

    props = clickData["properties"]

    return html.Div([
        html.B(f"Segment: {props.get('nm', 'N/A')}"),
        html.Br(),
        f"Length: {round(props.get('length', 0), 2)} meters",
        html.Br(),
        f"Gap Day: {props.get('gap_day', 'N/A')}"
    ])



@app.callback(
    Output('gap_histogram', 'figure'),
    Input('gap_column_selector', 'value')
)
def update_gap_histogram(selected_column):
    filtered = df_filtered.dropna(subset=[selected_column])
    fig = px.histogram(
        filtered,
        x=selected_column,
        nbins=30,
        labels={selected_column: selected_column.replace("_", " ").title()},
        color_discrete_sequence=["#08306b"]
    )
    fig.update_layout(title=f"Histogram of {selected_column.replace('_', ' ').title()}")
    return fig

@app.callback(
    Output("geojson", "hideout"),
    Output("map", "center"),     # zoom center
    Output("map", "zoom"),       # zoom level
    Input("scatter", "clickData"),
    Input("line_plot", "clickData"),
    State("geojson", "hideout")
)
def highlight_and_zoom(scatter_click, line_click, hideout):
    # Determine which input triggered the callback
    ctx = callback_context
    trigger = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

    if trigger == 'line_plot' and line_click:
        selected_id = line_click["points"][0]["customdata"][0]
    elif trigger == 'scatter' and scatter_click:
        selected_id = scatter_click["points"][0]["customdata"][0]
    else:
        return hideout, dash.no_update, dash.no_update

    hideout["highlight_id"] = selected_id

    for feature in geojson_data["features"]:
        if feature["properties"]["hwycovid"] == selected_id:
            coords = feature["geometry"]["coordinates"]
            mid_idx = len(coords) // 2
            center = coords[mid_idx][::-1]
            return hideout, center, 14

    return hideout, dash.no_update, dash.no_update

# === Run App ===
if __name__ == '__main__':
    app.run(debug=True, port=8050)
