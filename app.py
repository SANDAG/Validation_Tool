import os
import pandas as pd
import dash
from dash import Dash, html, dash_table, dcc
from dash import Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import dash_leaflet as dl
import numpy as np
from dash import callback_context
import dash_bootstrap_components as dbc
from load_data import load_data
from validation_plot_generator import build_scatter_plot, compute_overall_stats, build_source_ring_chart, create_map, make_vmt_fig, bar_scatter_layout,make_bar_figures,prepare_boarding_tables

data = load_data()
df1_all = data["df1"]
df2_all = data["df2"]
df3_all =  data["df3"]
df4_all =  data["df4"]
geojson_data = data["geojson_data"]
geojson_data_r = data["geojson_data_r"]
df_scenario = data['df_scenario']

scenario_id_list = df_scenario['scenario_id'].unique()
scenario_id_default = scenario_id_list[0]
df_filtered1 = df1_all[df1_all['scenario_id'] == scenario_id_default]
df_filtered2 = df2_all[df2_all['scenario_id'] == scenario_id_default]
df3 = df3_all[df3_all['scenario_id'] == scenario_id_default]
df4 = df4_all[df4_all['scenario_id'] == scenario_id_default]
    
# === Compute Overall Stats for Display ===
slope_all, r_squared_all, prmse_all, total_obs_all = compute_overall_stats(df_filtered2, 'count_day', 'day_flow')

# for truck
slope_all_t, r_squared_all_t, prmse_all_t, total_obs_all_t = compute_overall_stats(df3, 'truckaadt', 'truckflow')

# === Call Function to create map ===
initial_id = df_scenario["scenario_id"].iloc[0]
initial_geojson_link = geojson_data.get(initial_id, {"type": "FeatureCollection", "features": []})
initial_geojson_route = geojson_data_r.get(initial_id, {"type": "FeatureCollection", "features": []})
leaflet_map = create_map(initial_geojson_link, id_field="hwycovid")
leaflet_map_r =  create_map(initial_geojson_route, id_field="route_str")

# === Initialize Dash App ===
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server
app.title = "SANDAG Volume Validation Dashboard"

# === App Layout ===
# === Define Page 1 Layout: Volume Validation ===
def page_volume_validation():
    left_col, middle_col = bar_scatter_layout(
        bar_id='bar_fig',
        bar2_id='bar_fig2',
        count_id='count_fig',
        scatter_id='scatter',
        ring_id='source-ring',
        stat_id='stat-box',
        slope_all=slope_all,
        r_squared_all=r_squared_all,
        prmse_all=prmse_all,
        total_obs_all=total_obs_all,
        show_groupby_selector=True
    )

    return html.Div([
        left_col,
        middle_col,
        html.Div([
            html.H3("Map: Gap Day by Hwy Coverage ID"),
            leaflet_map
        ], style={'flex': '1', 'padding': '0px', 'boxSizing': 'border-box', 'height': '100%', 'width': '33.3%'})
    ], style={'display': 'flex', 'width': '100%', 'height': '700px'})

# ===truck page===
def page_truck_validation():
    left_col, middle_col = bar_scatter_layout(
        bar_id='truck_bar_fig',
        bar2_id='truck_bar_fig2',
        count_id='truck_count_fig',
        scatter_id='truck_scatter',
        ring_id='truck_source_ring',
        stat_id='truck_stat_box',
        slope_all=slope_all_t,
        r_squared_all=r_squared_all_t,
        prmse_all=prmse_all_t,
        total_obs_all=total_obs_all_t,
        show_groupby_selector=True
    )
    year_options = sorted(df3_all['est_year'].dropna().astype(int).unique())

    return html.Div([
        html.Div([ 
            html.Div([
                html.Div("Vehicle Type:", style={'marginRight': '10px'}),
                dcc.Dropdown(
                    id='vehicle_class_selector',
                    options=[
                        {'label': 'Truck', 'value': 'truck'},
                        {'label': 'LHD Truck', 'value': 'lhd'},
                        {'label': 'MHD Truck', 'value': 'mhd'},
                        {'label': 'HHD Truck', 'value': 'hhd'}
                    ],
                    value='truck',
                    clearable=False,
                    style={'width': '200px'}
                )
            ], style={'display': 'inline-block', 'marginRight': '20px'}),

            html.Div([
                html.Div("Year (filter only for scatter plot):", style={'marginRight': '10px'}),
                dcc.Dropdown(
                    id='year_selector',
                    options=[{'label': str(y), 'value': y} for y in year_options],
                    value=[],
                    multi=True,
                    placeholder='Select Year(s)',
                    style={'width': '600px'}
                )
            ], style={'display': 'inline-block'})
        ], style={'marginBottom': '10px', 'display': 'flex', 'gap': '20px'}),

        html.Div([
            left_col,
            middle_col,
            html.Div([
                html.H3("Map: Gap Day by Hwy Coverage ID"),
                leaflet_map
            ], style={'flex': '1', 'padding': '0px', 'boxSizing': 'border-box', 'height': '100%', 'width': '33.3%'})
        ], style={'display': 'flex', 'width': '100%', 'height': '700px'})
    ])
# === board page===
def page_board_validation():

    slope_all, r_squared_all, prmse_all, total_obs_all = compute_overall_stats(df4, 'board_day', 'day_board')

    left_col, middle_col= bar_scatter_layout(
        bar_id='board_bar_fig',
        bar2_id='board_bar_fig2',
        count_id='board_count_fig',
        scatter_id='board_scatter',
        ring_id='board_source_ring',
        stat_id='board_stat_box',
        slope_all=slope_all,
        r_squared_all=r_squared_all,
        prmse_all=prmse_all,
        total_obs_all=total_obs_all,
        show_groupby_selector=False
    )

    return html.Div([
        left_col,
        middle_col,
        html.Div([
            html.H3("Map: Gap Day by Route  ID"),
            leaflet_map_r
        ], style={'flex': '1', 'padding': '0px', 'boxSizing': 'border-box', 'height': '100%', 'width': '33.3%'})
    ], style={'display': 'flex', 'width': '100%', 'height': '700px'})

# === board table page===
def page_transit_boarding_summary():
    return  html.Div([
        html.H2("Boardings by Mode and TOD", style={'textAlign': 'center'}),
        html.Div(id='boarding_table_container')
    ])


# === Volume Validation by Hwy ===
def page_volume_by_hwy():
    all_corridors = sorted(df_filtered1['nm'].dropna().unique())
    corridor_options = [{'label': 'ALL', 'value': 'ALL'}] + [{'label': nm, 'value': nm} for nm in all_corridors]

    return html.Div([
        html.Div([
            html.H3("Select Corridor(s)"),
            dcc.Checklist(
                id='corridor_filter',
                options=corridor_options,
                value=['ALL'], # Select all by default
                inline=False,  # Display vertically
                style={ 'height': '800px'}  # Scroll if too many corridors
            )
        ], style={'width': '10%', 'padding': '5px', 'boxSizing': 'border-box'}),

        html.Div([
            html.H3("Line Chart: Model vs Observed by Segment"),

        html.Div([
            html.Div([
                html.Div([
                    html.Label("Time Period:", style={'marginRight': '10px'}),
                    dcc.Dropdown(
                        id='time_period_selector',
                        options=[{'label': i, 'value': i} for i in ['EA', 'AM', 'MD', 'PM', 'EV', 'Day']],
                        value='Day',
                        clearable=False,
                        style={'width': '150px'}
                    )
                ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '20px'}),

                html.Div([
                    html.Label("Y Axis Metric:", style={'marginRight': '10px'}),
                    dcc.Dropdown(
                        id='matrix_selector',
                        options=[
                            {'label': 'Flow', 'value': 'Flow'},
                            {'label': 'VMT', 'value': 'VMT'}
                        ],
                        value='Flow',
                        clearable=False,
                        style={'width': '150px'}
                    )
                ], style={'display': 'flex', 'alignItems': 'center'})
            ], style={'display': 'flex'})
        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '10px'}),
            html.Div([
                dcc.Graph(id='line_plot', style={'height': '450px', 'minWidth': '1000px'})
            ], style={'overflowX': 'auto', 'width': '100%'}),
            html.Div([
                html.Div([
                    dash_table.DataTable(
                        id='summary_table',
                        columns=[],  # Will be set dynamically
                        data=[],
                        style_table={'overflowX': 'auto', 'maxHeight': '250px', 'overflowY': 'auto'},
                        style_cell={'textAlign': 'center', 'padding': '5px'},
                        style_header={'fontWeight': 'bold'}
                    )
                ], style={'width': '70%', 'padding': '10px','marginTop':'10px'}),

                html.Div([
                    dcc.Graph(id='dir_ring_graph', config={'displayModeBar': False}, style={'height': '250px'})
                ], style={'width': '30%', 'padding': '10px'})
            ], style={'display': 'flex', 'justifyContent': 'space-between','marginTop':'10px'})

        ], style={'width': '60%', 'padding': '10px', 'boxSizing': 'border-box'}),


        html.Div([
            html.H3("Map: Gap Day by Hwy Coverage ID"),
            leaflet_map
        ], style={'width': '30%', 'padding': '5px', 'boxSizing': 'border-box','height':'800px'})
    ], style={'display': 'flex', 'width': '100%', 'height': '700px'})

# === Define Page 3 Layout: VMT===
def page_vmt_comparison():

    return html.Div([
        html.H2("VMT Comparison: Model vs Observed by Different Groups", style={'textAlign': 'center', 'marginBottom': '10px'}),

        html.Div([
            # Row 1
            html.Div([
                dcc.Graph(figure=make_vmt_fig(df_filtered2,'pmsa_nm', 'By PMSA'), style={'width': '50%', 'height': '100%'}),
                dcc.Graph(figure=make_vmt_fig(df_filtered2,'vcategory', 'By Category'), style={'width': '50%', 'height': '100%'})
            ], style={'display': 'flex', 'height': '50%'}),

            # Row 2
            html.Div([
                dcc.Graph(figure=make_vmt_fig(df_filtered2,'city_nm', 'By City'), style={'width': '50%', 'height': '100%'}),
                dcc.Graph(figure=make_vmt_fig(df_filtered2,'rdclass', 'By Road Class'), style={'width': '50%', 'height': '100%'})
            ], style={'display': 'flex', 'height': '50%'})
        ], style={'height': '700px'})
    ], style={'padding': '10px', 'height': '700px', 'boxSizing': 'border-box',})

scenario_options = [
{"label": f"{row['scenario_id']}: {row['scenario_name']}", "value": row["scenario_id"]}
for _, row in df_scenario.iterrows()]

# === Full App Layout with Collapsible Sidebar ===
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),

    # === Fixed Top Bar ===
    html.Div([
        html.Button("☰ Menu", id="menu-button", n_clicks=0, style={'marginRight': '10px'}),
        html.Div("Scenario:", style={'marginRight': '5px', 'fontWeight': 'bold'}),
        dcc.Dropdown(
            id='scenario_selector',
            options=scenario_options,
            value= scenario_id_list[0],  # default
            clearable=False,
            style={'width': '300px'}
        )
    ], style={
        'position': 'fixed',
        'top': '0',
        'left': '0',
        'width': '100%',
        'backgroundColor': 'white',
        'padding': '10px 20px',
        'zIndex': '1001',
        'display': 'flex',
        'alignItems': 'center',
        'gap': '10px',
        'fontFamily': 'Open Sans, verdana, arial, sans-serif',
        'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
    }),

    # === Sidebar (starts after top bar) ===
    html.Div(id='sidebar-content', children=[
        html.H2(" "),
        html.Hr(),

        html.Div("All Class", style={'fontWeight': 'bold', 'margin': '20px 0 0 10px'}),
        dcc.Link("All Class Volume Validation", href="/", style={'display': 'block', 'marginLeft': '20px'}),
        dcc.Link("All Class VMT Validation", href="/vmt_comparison", style={'display': 'block', 'marginLeft': '20px'}),

        html.Div("Highway", style={'fontWeight': 'bold', 'margin': '20px 0 0 10px'}),
        dcc.Link("Highway Volume & VMT Validation", href="/volume_by_hwy", style={'display': 'block', 'marginLeft': '20px'}),

        html.Div("Truck", style={'fontWeight': 'bold', 'margin': '20px 0 0 10px'}),
        dcc.Link("Truck Volume Validation", href="/truck_validation", style={'display': 'block', 'marginLeft': '20px'}),

        html.Div("Transit", style={'fontWeight': 'bold', 'margin': '20px 0 0 10px'}),
        dcc.Link("Transit Volume Validation", href="/transit_validation", style={'display': 'block', 'marginLeft': '20px'}),
        dcc.Link("Transit Boarding Summary", href="/transit_boarding_summary", style={'display': 'block', 'marginLeft': '20px'}),
    ],  style={
        'position': 'fixed',
        'top': '60px', 
        'left': '-200px',
        'width': '200px',
        'height': 'calc(100vh - 60px)',
        'backgroundColor': '#f8f9fa',
        'padding': '20px',
        'fontSize': '14px',
        'boxSizing': 'border-box',
        'zIndex': '1000',
        'fontFamily': 'Open Sans, verdana, arial, sans-serif',
        'transition': 'left 0.3s'
    }),

    # === Page Content  ===
    html.Div(id='page-content', style={
        'marginLeft': '0px',
        'transition': 'margin-left 0.3s',
        'padding': '60px 20px 20px 20px', 
        'fontFamily': 'Open Sans, verdana, arial, sans-serif'
    }),
    # === SANDAG Logo ===
    html.Img(
        src='/assets/sandag-logo.png',
        style={
            'position': 'fixed',
            'top': '10px',
            'right': '10px',
            'height': '40px',
            'zIndex': '1002'
        }
    )
])


@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname'),
    Input('scenario_selector', 'value')
)
def update_page(pathname, scenario_id):
    global df_filtered1, df_filtered2, df3, df4

    df_filtered1 = df1_all[df1_all['scenario_id'] == scenario_id]
    df_filtered2 = df2_all[df2_all['scenario_id'] == scenario_id]
    df3 = df3_all[df3_all['scenario_id'] == scenario_id]
    df4 = df4_all[df4_all['scenario_id'] == scenario_id]

    if pathname == '/volume_by_hwy':
        return page_volume_by_hwy()
    elif pathname == '/vmt_comparison':
        return page_vmt_comparison()
    elif pathname == '/truck_validation':
        return page_truck_validation()
    elif pathname == '/transit_validation':
        return page_board_validation()
    elif pathname == '/transit_boarding_summary':
        return page_transit_boarding_summary()
    return page_volume_validation()



# === Collapsible Sidebar Toggle ===
@app.callback(
    Output('sidebar-content', 'style'),
    Output('page-content', 'style'),
    Input('menu-button', 'n_clicks'),
    State('sidebar-content', 'style'),
    State('page-content', 'style')
)
def toggle_sidebar(n, sidebar_style, page_style):
    if n % 2 == 1:
        sidebar_style['left'] = '0px'
        page_style['marginLeft'] = '180px'
    else:
        sidebar_style['left'] = '-180px'
        page_style['marginLeft'] = '0px'
    return sidebar_style, page_style



# === Popup Window in Map Callback ===
@app.callback(
    Output("popup", "children"),
    Input("geojson", "clickData")
)
def show_popup(clickData):
    
    if not clickData or "properties" not in clickData:
        return "No feature selected"

    props = clickData["properties"]
    labels = {
        "hwycovid": "Hwy ID",
        "route_name_id": "Route ID",
        "gap_day_all_class": "Volume Gap Day (All Class)",
        "vmt_gap_day_all_class": "VMT Gap Day (All Class)",
        "gap_day_truck": "Truck Volume Gap Day",
        "vmt_gap_day_truck": "Truck VMT Gap Day",
        "transit_gap_day": "Transit Gap Day"
    }

    return html.Div([
        html.Div(f"{label}: {props[key]}%") if 'gap' in key or 'vmt' in key else html.Div(f"{label}: {props[key]}")
        for key, label in labels.items() if key in props and props[key] is not None
    ])

# === Map Highlight Callback ===
def get_map_center(selected_id, hideout, df, id):
    hideout["highlight_id"] = selected_id
    hideout["id_field"] = id
    for feature in df["features"]:
        if str(feature["properties"].get(id)) == str(selected_id):
            coords = feature["geometry"]["coordinates"]
            print(f"🔍 Geometry type: {feature['geometry']['type']}")
            print(f"🔍 Raw coords: {coords[:2]}")
            mid_idx = len(coords) // 2
            center = coords[mid_idx][::-1]
            return hideout, center, 14
    return hideout, dash.no_update, dash.no_update

@app.callback(
    Output("geojson", "hideout", allow_duplicate=True),
    Output("map", "center", allow_duplicate=True),
    Output("map", "zoom", allow_duplicate=True),
    Input("line_plot", "clickData"),
    State("geojson", "hideout"),
    State("scenario_selector", "value"),
    prevent_initial_call=True
)
def zoom_from_line(clickData, hideout,scenario_id):
    if not clickData:
        return hideout, dash.no_update, dash.no_update

    selected_id = clickData["points"][0]["customdata"][0]
    geojson = geojson_data.get(scenario_id, {"type": "FeatureCollection", "features": []})
    return get_map_center(selected_id, hideout,geojson, 'hwycovid')

@app.callback(
    Output("geojson", "hideout"),
    Output("map", "center"),
    Output("map", "zoom"),
    Input("scatter", "clickData"),
    State("geojson", "hideout"),
    State("scenario_selector", "value")
)
def zoom_from_scatter(clickData, hideout,scenario_id):
    if not clickData:
        return hideout, dash.no_update, dash.no_update

    selected_id = clickData["points"][0]["customdata"][0]
    geojson = geojson_data.get(scenario_id, {"type": "FeatureCollection", "features": []})
    print(f"🧭 Selected ID: {selected_id}")
    print(f"🧭 Features available: {len(geojson.get('features', []))}")
    return get_map_center(selected_id, hideout, geojson, 'hwycovid')

@app.callback(
    Output("geojson", "hideout", allow_duplicate=True),
    Output("map", "center", allow_duplicate=True),
    Output("map", "zoom", allow_duplicate=True),
    Input("truck_scatter", "clickData"),
    State("geojson", "hideout"),
    State("scenario_selector", "value"),
    prevent_initial_call=True
)
def zoom_from_truck_scatter(clickData, hideout,scenario_id):
    if not clickData:
        return hideout, dash.no_update, dash.no_update
    selected_id = clickData["points"][0]["customdata"][0]
    geojson = geojson_data.get(scenario_id, {"type": "FeatureCollection", "features": []})
    return get_map_center(selected_id, hideout,geojson, 'hwycovid')

@app.callback(
    Output("geojson", "hideout", allow_duplicate=True),
    Output("map", "center", allow_duplicate=True),
    Output("map", "zoom", allow_duplicate=True),
    Input("board_scatter", "clickData"),
    State("geojson", "hideout"),
    State("scenario_selector", "value"),
    prevent_initial_call=True
)
def zoom_from_board_scatter(clickData, hideout,scenario_id):
    if not clickData:
        return hideout, dash.no_update, dash.no_update

    selected_id = clickData["points"][0]["customdata"][0]
    geojson = geojson_data_r.get(scenario_id, {"type": "FeatureCollection", "features": []})
    return get_map_center(selected_id, hideout,geojson, 'route_str')

# === Bar Graph Callback ===
from plotly import graph_objects as go

@app.callback(
    Output('bar_fig', 'figure'),
    Output('bar_fig2', 'figure'),
    Output('count_fig', 'figure'),
    Output('scatter', 'figure'),
    Output('source-ring', 'figure'),
    Output('stat-box', 'children'),  
    Input('bar_fig', 'clickData'),
    Input('bar_fig2', 'clickData'),
    Input('count_fig', 'clickData'),
    Input('groupby_selector', 'value'),
    Input('scenario_selector', 'value'),
    State('bar_fig', 'figure'),
    prevent_initial_call=False
)
def update_all(click1, click2, click3, groupby_col, scenario_id, current_fig1):
    ctx = callback_context
    trigger = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
    df_filtered2 = df2_all[df2_all['scenario_id'] == scenario_id]
    df3 = df3_all[df3_all['scenario_id'] == scenario_id]

    # Select correct data and columns
    df = df_filtered2.copy()
    model_col, obs_col = 'day_flow', 'count_day'

    # Get x-axis fixed order
    if current_fig1 and 'data' in current_fig1 and len(current_fig1['data']) > 0:
        x_axis_fixed = current_fig1['data'][0]['x']
    else:
        x_axis_fixed = None

    # Determine selected group
    selected_group = None
    clicked = ctx.triggered[0]['value']
    if trigger in ['bar_fig', 'bar_fig2', 'count_fig'] and clicked and 'points' in clicked:
        clicked_label = clicked['points'][0]['x']
        if clicked_label == getattr(update_all, 'last_selected', None):
            selected_group = None
        else:
            selected_group = clicked_label
        update_all.last_selected = selected_group
    else:
        update_all.last_selected = None

    # Bar chart stats (R², slope, PRMSE)
    results, count_results = [], []
    for group_val, group in df.groupby(groupby_col):
        x = pd.to_numeric(group[obs_col], errors='coerce')
        y = pd.to_numeric(group[model_col], errors='coerce')
        mask = ~np.isnan(x) & ~np.isnan(y)
        x_clean, y_clean = x[mask], y[mask]

        if len(x_clean) > 1:
            slope, intercept = np.polyfit(x_clean, y_clean, 1)
            y_pred = slope * x_clean + intercept
            r_squared = 1 - np.sum((y_clean - y_pred) ** 2) / np.sum((y_clean - y_clean.mean()) ** 2)
            rmse = np.sqrt(np.mean((y_clean - y_pred) ** 2))
            prmse = (rmse / y_clean.mean()) * 100 if y_clean.mean() != 0 else np.nan
            results.append({'Group': group_val, 'R_squared': round(r_squared, 2),
                            'Slope': round(slope, 2), 'PRMSE': round(prmse, 2)})

        count_results.append({'Group': group_val, 'Num_Observed': len(group)})

    result_df = pd.DataFrame(results)
    count_df = pd.DataFrame(count_results)

    if x_axis_fixed is None:
        x_axis_fixed = list(result_df['Group'])

    # === Bar Charts ===
    bar_fig, bar_fig2, count_fig = make_bar_figures(result_df, count_df, selected_group, x_axis_fixed)

    # === Scatter Plot ===
    if selected_group:
        sub_df = df[df[groupby_col] == selected_group]
    else:
        sub_df = df

    scatter_df = sub_df[[obs_col, model_col, 'hwycovid']].dropna()
    x, y = scatter_df[obs_col], scatter_df[model_col]
    slope, intercept = np.polyfit(x, y, 1)
    line_x = np.linspace(x.min(), x.max(), 100)
    line_y = slope * line_x + intercept

    scatter_fig, r_squared, slope, prmse = build_scatter_plot(sub_df, obs_col, model_col,'hwycovid')

    # === Source Ring Chart ===
    ring_fig = build_source_ring_chart(sub_df)

    # === Statistics Box ===
    stat_box = html.Div([
        html.Div([html.H3(f"{slope:.2f}"), html.Small("Slope")], style={'textAlign': 'center'}),
        html.Div([html.H3(f"{r_squared:.2f}"), html.Small("R²")], style={'textAlign': 'center'}),
        html.Div([html.H3(f"{prmse:.2f}%"), html.Small("PRMSE")], style={'textAlign': 'center'}),
        html.Div([html.H3(f"{len(scatter_df)}"), html.Small("Count")], style={'textAlign': 'center'})
    ], style={'display': 'flex', 'flexDirection': 'column', 'justifyContent': 'center'})

    return bar_fig, bar_fig2, count_fig, scatter_fig, ring_fig, stat_box

@app.callback(
    Output('truck_bar_fig', 'figure'),
    Output('truck_bar_fig2', 'figure'),
    Output('truck_count_fig', 'figure'),
    Output('truck_scatter', 'figure'),
    Output('truck_source_ring', 'figure'),
    Output('truck_stat_box', 'children'),  
    Input('truck_bar_fig', 'clickData'),
    Input('truck_bar_fig2', 'clickData'),
    Input('truck_count_fig', 'clickData'),
    Input('groupby_selector', 'value'),
    Input('scenario_selector', 'value'),
    Input('vehicle_class_selector', 'value'),
    Input('year_selector', 'value'),
    State('truck_bar_fig', 'figure'),
    prevent_initial_call=False
)
def update_truck(click1, click2, click3, groupby_col, scenario_id, vehicle_class, year_values, current_fig1):
    ctx = callback_context
    trigger = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
    df3 = df3_all[df3_all['scenario_id'] == scenario_id]

    # Select correct data and columns
    if vehicle_class == 'truck':
        df = df3.copy()
        model_col, obs_col = 'truckflow', 'truckaadt'
    elif vehicle_class == 'lhd':
        df = df3.copy()
        model_col, obs_col = 'lhdtruckflow', 'lhdtruckaadt'
    elif vehicle_class == 'mhd':
        df = df3.copy()
        model_col, obs_col = 'mhdtruckflow', 'mhdtruckaadt'
    elif vehicle_class == 'hhd':
        df = df3.copy()
        model_col, obs_col = 'hhdtruckflow', 'hhdtruckaadt'
    else:
        return dash.no_update

    # Get x-axis fixed order
    if current_fig1 and 'data' in current_fig1 and len(current_fig1['data']) > 0:
        x_axis_fixed = current_fig1['data'][0]['x']
    else:
        x_axis_fixed = None

    # Determine selected group
    selected_group = None
    clicked = ctx.triggered[0]['value']
    if trigger in ['truck_bar_fig', 'truck_bar_fig2', 'truck_count_fig'] and clicked and 'points' in clicked:
        clicked_label = clicked['points'][0]['x']
        if clicked_label == getattr(update_all, 'last_selected', None):
            selected_group = None
        else:
            selected_group = clicked_label
        update_all.last_selected = selected_group
    else:
        update_all.last_selected = None

    # Bar chart stats (R², slope, PRMSE)
    results, count_results = [], []
    for group_val, group in df.groupby(groupby_col):
        x = pd.to_numeric(group[obs_col], errors='coerce')
        y = pd.to_numeric(group[model_col], errors='coerce')
        mask = ~np.isnan(x) & ~np.isnan(y)
        x_clean, y_clean = x[mask], y[mask]

        if len(x_clean) > 1:
            slope, intercept = np.polyfit(x_clean, y_clean, 1)
            y_pred = slope * x_clean + intercept
            r_squared = 1 - np.sum((y_clean - y_pred) ** 2) / np.sum((y_clean - y_clean.mean()) ** 2)
            rmse = np.sqrt(np.mean((y_clean - y_pred) ** 2))
            prmse = (rmse / y_clean.mean()) * 100 if y_clean.mean() != 0 else np.nan
            results.append({'Group': group_val, 'R_squared': round(r_squared, 2),
                            'Slope': round(slope, 2), 'PRMSE': round(prmse, 2)})

        count_results.append({'Group': group_val, 'Num_Observed': len(group)})

    result_df = pd.DataFrame(results)
    count_df = pd.DataFrame(count_results)

    if x_axis_fixed is None:
        x_axis_fixed = list(result_df['Group'])

    # === Bar Charts ===
    bar_fig, bar_fig2, count_fig = make_bar_figures(result_df, count_df, selected_group, x_axis_fixed)

    # === Scatter Plot ===
    if selected_group:
        sub_df = df[df[groupby_col] == selected_group]
    else:
        sub_df = df

    if year_values:
        scatter_df = sub_df[sub_df['est_year'].isin(year_values)]
    else:
        scatter_df = sub_df

    scatter_df = scatter_df[[obs_col, model_col, 'hwycovid']].dropna()
    x, y = scatter_df[obs_col], scatter_df[model_col]
    slope, intercept = np.polyfit(x, y, 1)
    line_x = np.linspace(x.min(), x.max(), 100)
    line_y = slope * line_x + intercept

    scatter_fig, r_squared, slope, prmse = build_scatter_plot(scatter_df, obs_col, model_col,'hwycovid')

    # === Source Ring Chart ===
    ring_fig = build_source_ring_chart(sub_df)

    # === Statistics Box ===
    stat_box = html.Div([
        html.Div([html.H3(f"{slope:.2f}"), html.Small("Slope")], style={'textAlign': 'center'}),
        html.Div([html.H3(f"{r_squared:.2f}"), html.Small("R²")], style={'textAlign': 'center'}),
        html.Div([html.H3(f"{prmse:.2f}%"), html.Small("PRMSE")], style={'textAlign': 'center'}),
        html.Div([html.H3(f"{len(scatter_df)}"), html.Small("Count")], style={'textAlign': 'center'})
    ], style={'display': 'flex', 'flexDirection': 'column', 'justifyContent': 'center'})

    return bar_fig, bar_fig2, count_fig, scatter_fig, ring_fig, stat_box

@app.callback(
    Output('board_bar_fig', 'figure'),
    Output('board_bar_fig2', 'figure'),
    Output('board_count_fig', 'figure'),
    Output('board_scatter', 'figure'),
    Output('board_source_ring', 'figure'),
    Output('board_stat_box', 'children'),  
    Input('board_bar_fig', 'clickData'),
    Input('board_bar_fig2', 'clickData'),
    Input('board_count_fig', 'clickData'),
    Input('scenario_selector', 'value'),
    State('board_bar_fig', 'figure'),
    prevent_initial_call=False
)
def update_board(click1, click2, click3, scenario_id, current_fig1):
    ctx = callback_context
    trigger = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

    df = df4_all[df4_all['scenario_id'] == scenario_id]
    groupby_col = 'mode_name'
    obs_col = 'board_day'
    model_col = 'day_board'

    # Get x-axis fixed order
    if current_fig1 and 'data' in current_fig1 and len(current_fig1['data']) > 0:
        x_axis_fixed = current_fig1['data'][0]['x']
    else:
        x_axis_fixed = None

    # Determine selected group
    selected_group = None
    clicked = ctx.triggered[0]['value']
    if trigger in ['board_bar_fig', 'board_bar_fig2', 'board_count_fig'] and clicked and 'points' in clicked:
        clicked_label = clicked['points'][0]['x']
        if clicked_label == getattr(update_board, 'last_selected', None):
            selected_group = None
        else:
            selected_group = clicked_label
        update_board.last_selected = selected_group
    else:
        update_board.last_selected = None

    # Bar Figures
    result_df = []
    count_df = []

    for group_val, group in df.groupby(groupby_col):
        slope, r2, prmse, count = compute_overall_stats(group, obs_col, model_col)

        result_df.append({'Group': group_val, 'R_squared': round(r2, 2),
                            'Slope': round(slope, 2), 'PRMSE': round(prmse, 2)})
        count_df.append({'Group': group_val, 'Num_Observed': count})

    result_df = pd.DataFrame(result_df)
    count_df = pd.DataFrame(count_df)

    bar_fig, bar_fig2, count_fig = make_bar_figures(result_df, count_df, selected_group, x_axis_fixed)

    # Scatter
    sub_df = df[df[groupby_col] == selected_group] if selected_group else df
    scatter_fig, r_squared, slope, prmse = build_scatter_plot(sub_df, obs_col, model_col,'route')

    # Ring chart
    ring_fig = build_source_ring_chart(sub_df)

    # Stat box
    stat_box = html.Div([
        html.Div([html.H3(f"{slope:.2f}"), html.Small("Slope")], style={'textAlign': 'center'}),
        html.Div([html.H3(f"{r_squared:.2f}"), html.Small("R²")], style={'textAlign': 'center'}),
        html.Div([html.H3(f"{prmse:.2f}%"), html.Small("PRMSE")], style={'textAlign': 'center'}),
        html.Div([html.H3(f"{len(sub_df)}"), html.Small("Count")], style={'textAlign': 'center'})
    ], style={'display': 'flex', 'flexDirection': 'column', 'justifyContent': 'center'})

    return bar_fig, bar_fig2, count_fig, scatter_fig, ring_fig, stat_box


@app.callback(
    Output('line_plot', 'figure'),
    Input('corridor_filter', 'value'),
    Input('scenario_selector', 'value'),
    Input('time_period_selector', 'value'),
    Input('matrix_selector', 'value')
)
def update_line_chart(selected_corridors, scenario_id, selected_period, selected_metric):
    # Choose correct DataFrame
    base_df = df1_all[df1_all['scenario_id'] == scenario_id]

    # Filter corridor
    if not selected_corridors:
        filtered_df = base_df.iloc[0:0]
    elif 'ALL' in selected_corridors:
        filtered_df = base_df
    else:
        filtered_df = base_df[base_df['nm'].isin(selected_corridors)]

    # Define column names
    if selected_period == 'Day':
        obs_col = {
            'Flow': 'count_day',
            'VMT': 'vmt_day',
        }[selected_metric]
        model_col = {
            'Flow': 'day_flow',
            'VMT': 'day_vmt',
        }[selected_metric]
    else:
        period_lc = selected_period.lower()

        obs_col = {
            'Flow': f'count_{period_lc}',
            'VMT': f'vmt_{period_lc}',
        }[selected_metric]

        model_col = {
            'Flow': f'{period_lc}_flow',
            'VMT': f'{period_lc}_vmt',
        }[selected_metric]


    # Fallback if missing columns
    if obs_col not in filtered_df.columns or model_col not in filtered_df.columns:
        fig = go.Figure()
        fig.update_layout(title='Selected combination not available in data.')
        return fig

    # Plot
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=filtered_df['hwycovid'],
        y=filtered_df[model_col],
        customdata=filtered_df[['hwycovid']],
        mode='lines+markers',
        name=f'Model {model_col}',
        line=dict(color='#08306b'),
        connectgaps=False
    ))

    fig.add_trace(go.Scatter(
        x=filtered_df['hwycovid'],
        y=filtered_df[obs_col],
        customdata=filtered_df[['hwycovid']],
        mode='lines+markers',
        name=f'Observed {obs_col}',
        line=dict(color='#F65166'),
        connectgaps=False
    ))

    fig.update_layout(
        xaxis_title='Highway Segment',
        yaxis_title=selected_metric,
        height=600,
        width=max(1000, len(filtered_df) * 20),
        margin=dict(l=20, r=20, t=5, b=5),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0),
        xaxis=dict(
            type='category',
            tickangle=45,
            tickmode='array',
            tickvals=filtered_df['hwycovid'],
            ticktext=filtered_df['label'],
            tickfont=dict(size=10),
            showgrid=False,
            range=[-0.7, len(filtered_df) - 0.7]
        )
    )

    return fig

#update table and ring graph in page 2 accoridng to matrix and corridor selected
@app.callback(
    Output('summary_table', 'columns'),
    Output('summary_table', 'data'),
    Output('dir_ring_graph', 'figure'),
    Input('corridor_filter', 'value'),
    Input('matrix_selector', 'value'),
    Input('scenario_selector', 'value'),
)
def update_table_and_ring(corridors, metric,scenario_id):

    df_base = df1_all[df1_all['scenario_id'] == scenario_id]

    columns_to_show = ['hwycovid', 'nm', 'fxnm', 'txnm','dir_nm', 'count_day', 'day_flow', 'day_vmt', 'vmt_day']

    if not corridors or 'ALL' in corridors:
        df_subset = df_base
    else:
        df_subset = df_base[df_base['nm'].isin(corridors)]

    df_subset = df_subset[columns_to_show]

    # Create table
    columns = [{"name": col, "id": col} for col in df_subset.columns]
    data = df_subset.to_dict('records')

    # Ring chart for 'dir_nm'
    # Group by source and drop NaNs
    source_dist = df_subset['dir_nm'].dropna().value_counts().reset_index()
    source_dist.columns = ['dir_nm', 'Count']
    source_dist['Percent'] = round(100 * source_dist['Count'] / source_dist['Count'].sum())

    direction_color_map = {
        'NB': '#08306b',
        'SB': '#F65166',
        'EB': '#49C2D6',
        'WB': '#F6C800'
    }

    # Assign colors
    colors = [direction_color_map.get(dir_val, '#CCCCCC') for dir_val in source_dist['dir_nm']]

    # Build pie chart (ring)
    fig = go.Figure(go.Pie(
        labels=source_dist['dir_nm'],
        values=source_dist['Percent'],
        hole=0.6,
        textinfo='label+percent',
        marker=dict(colors=colors)
    ))
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), showlegend=False)

    return columns, data, fig

@app.callback(
    Output('boarding_table_container', 'children'),
    Input('scenario_selector', 'value')
)
def update_boarding_tables(scenario_id):
    df4 = df4_all[df4_all['scenario_id'] == scenario_id]
    observed, model, diff, gap = prepare_boarding_tables(df4)

    def make_table(df, title):
        return html.Div([
            html.H4(title),
            dash_table.DataTable(
                columns=[{"name": col.upper(), "id": col} for col in df.reset_index().columns],
                data=df.reset_index().to_dict("records"),
                style_table={'overflowX': 'auto'},
                style_cell={'padding': '4px', 'textAlign': 'center'},
                style_header={'fontWeight': 'bold', 'backgroundColor': '#f0f0f0'}
            )
        ], style={'margin': '10px', 'width': '48%'})

    return html.Div([
        html.Div([
            make_table(observed, "Observed Boardings"),
            make_table(diff, "Boardings Difference"),
        ], style={'display': 'flex', 'justifyContent': 'space-between'}),

        html.Div([
            make_table(model, "Model Boardings"),
            make_table(gap, "Boardings Gap(%)"),
        ], style={'display': 'flex', 'justifyContent': 'space-between'})
    ])

@app.callback(
    Output("geojson", "data", allow_duplicate=True),
    Output("geojson", "hideout", allow_duplicate=True),
    Input("scenario_selector", "value"),
    State("url", "pathname"),
    prevent_initial_call=True
)
def update_geojson_by_scenario(scenario_id, pathname):
    if pathname == "/transit_validation":
        data = geojson_data_r.get(scenario_id, {"type": "FeatureCollection", "features": []})
        print(f"🚌 [Transit] scenario_id {scenario_id} → {len(data['features'])} features")
        return data, {"highlight_id": None, "id_field": "route_str"}
    else:
        data = geojson_data.get(scenario_id, {"type": "FeatureCollection", "features": []})
        print(f"🛣️ [Hwy] scenario_id {scenario_id} → {len(data['features'])} features")
        return data, {"highlight_id": None, "id_field": "hwycovid"}

# === Run App ===
if __name__ == '__main__':
    app.run(debug=True)