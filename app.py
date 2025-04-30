import pandas as pd
import dash
from dash import Dash, html, dash_table, dcc
from dash import Input, Output, State
import plotly.express as px
import json
import dash_leaflet as dl
from dash_extensions.javascript import assign
import numpy as np
import plotly.graph_objects as go
from dash import callback_context
import dash_bootstrap_components as dbc


# === Load Excel Sheets ===
df = pd.read_excel("vis_worksheet.xlsx", sheet_name='fwy_worksheet')
df2 = pd.read_excel("vis_worksheet.xlsx", sheet_name='allclass_worksheet')

# === Load GeoJSON ===
with open("Joined_hwy.geojson", "r") as f:
    geojson_data = json.load(f)

# === Filter columns for preview table ===
# selected_columns = ['nm', 'count_day', 'count_ea', 'count_am', 'count_md', 'count_pm', 'count_ev', 'source','DAY_Flow','pmsa_nm','gap_day','hwycovid']
df_filtered = df.copy()
df_filtered1 = df_filtered.dropna(subset=['count_day', 'DAY_Flow'])
df_filtered2 = df2.dropna(subset=['count_day', 'DAY_Flow'])

# === Create line plot: hwycovid (label) vs count_day and DAY_Flow ===
line_df = df_filtered1.copy()
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
    line=dict(color='#F65166')
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
        tickfont=dict(size=8),
        showgrid=False,
        range=[-0.9, len(line_df) - 0.9]  # 👈 eliminate extra padding
    )
)

# === Scatter Plot: count_day vs DAY_Flow ===
scatter_df = df_filtered2[['count_day', 'DAY_Flow','hwycovid']].dropna()
x = scatter_df['count_day']
y = scatter_df['DAY_Flow']
slope, intercept = np.polyfit(x, y, 1)
line_x = np.linspace(x.min(), x.max(), 100)
line_y = slope * line_x + intercept
r_squared = 1 - np.sum((y - (slope * x + intercept)) ** 2) / np.sum((y - y.mean()) ** 2)

scatter_fig = px.scatter(
    scatter_df,
    x='count_day',
    y='DAY_Flow',
    custom_data=['hwycovid'],
    labels={'count_day': 'Observed Count', 'DAY_Flow': 'Model Flow'},
    color_discrete_sequence=["#08306b"],
    opacity=0.6
)

# Modify marker size for all points
scatter_fig.update_traces(marker=dict(size=9)) 

# Add regression line
scatter_fig.add_trace(go.Scatter(
    x=line_x,
    y=line_y,
    mode='lines',
    name='Best Fit Line',
    line=dict(color='#F65166', dash='dash',width=3)
))


# === Calculate R² slope and PRMSE per PMSA ===
results = []

for pmsa, group in df_filtered2.groupby('pmsa_nm'):
    x = pd.to_numeric(group['count_day'], errors='coerce')
    y = pd.to_numeric(group['DAY_Flow'], errors='coerce')
    
    mask = ~np.isnan(x) & ~np.isnan(y)
    x_clean = x[mask]
    y_clean = y[mask]

    if len(x_clean) > 1:
        slope, intercept = np.polyfit(x_clean, y_clean, 1)
        y_pred = slope * x_clean + intercept
        r_squared = 1 - np.sum((y_clean - y_pred) ** 2) / np.sum((y_clean - y_clean.mean()) ** 2)
        
        rmse = np.sqrt(np.mean((y_clean - y_pred) ** 2))
        mean_obs = np.mean(y_clean)
        prmse = (rmse / mean_obs) * 100 if mean_obs != 0 else np.nan

        results.append({
            'PMSA': pmsa,
            'R_squared': round(r_squared, 2),
            'Slope': round(slope, 2),
            'PRMSE': round(prmse, 2)
        })

r2slope_df = pd.DataFrame(results)


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
            color = '#485187';
        } else if (gap < 0) {
            color = '#6C649F';
        } else if (gap < 5) {
            color = '#9057A3';
        } else if (gap < 10) {
            color = '#B44691';
        } else {
            color = '#F65166';
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
app = Dash(__name__, suppress_callback_exceptions=True)
app.title = "SANDAG Volume Validation Dashboard"


# === Create Leaflet Map ===
leaflet_map = dl.Map(
    id='map',
    center=[32.9, -117],
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
                html.Div("-10 ≤ Gap < -5", style={'color': '#485187'}),
                html.Div("-5 ≤ Gap < 0", style={'color': '#6C649F'}),
                html.Div("0 ≤ Gap < 5", style={'color': '#9057A3'}),
                html.Div("5 ≤ Gap < 10", style={'color': '#B44691'}),
                html.Div("Gap ≥ 10", style={'color': '#F65166'})
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
    style={'width': '100%', 'height': '100%'}
)

# === Compute Overall Stats for Display ===
x_all = pd.to_numeric(df_filtered2['count_day'], errors='coerce')
y_all = pd.to_numeric(df_filtered2['DAY_Flow'], errors='coerce')
mask_all = ~np.isnan(x_all) & ~np.isnan(y_all)
x_clean_all = x_all[mask_all]
y_clean_all = y_all[mask_all]

slope_all, intercept_all = np.polyfit(x_clean_all, y_clean_all, 1)
y_pred_all = slope_all * x_clean_all + intercept_all
r_squared_all = 1 - np.sum((y_clean_all - y_pred_all) ** 2) / np.sum((y_clean_all - y_clean_all.mean()) ** 2)
rmse_all = np.sqrt(np.mean((y_clean_all - y_pred_all) ** 2))
mean_obs_all = np.mean(y_clean_all)
prmse_all = (rmse_all / mean_obs_all) * 100 if mean_obs_all != 0 else np.nan
total_obs_all = len(x_clean_all)


# === Create Ring Chart for 'source' Distribution ===
source_color_map = {
    'PeMS': '#08306b',       # Moonshine
    'San Diego': '#F6C800',  # Sunshine
    'Chula Vista': '#F65166',# Confetti
    'Carlsbad': '#49C2D6',   # Splash
    'El Cajon': '#F2762E',   # Squash
    'Oceanside': '#2E87C8',    # Sky
    'Del Mar': '#A3E7D8',     # Mint
    'Coronado': '#C3B1E1'      # Lavender
}

# Build initial donut chart with fixed color mapping
source_dist = df_filtered2['source'].value_counts().reset_index()
source_dist.columns = ['Source', 'Count']
source_dist['Percent'] = round(100 * source_dist['Count'] / source_dist['Count'].sum())

# Apply color mapping
colors = [source_color_map.get(src, '#CCCCCC') for src in source_dist['Source']]

source_fig = go.Figure(go.Pie(
    labels=source_dist['Source'],
    values=source_dist['Percent'],
    hole=0.6,
    textinfo='label+percent',
    marker=dict(colors=colors)
))


# === App Layout ===
# === Define Page 1 Layout: Volume Validation ===
def page_volume_validation():
    return html.Div([
        html.Div([
            html.Div([
                html.H3("R² and Slope", style={'marginRight': '20px'}),
                dcc.Dropdown(
                    id='groupby_selector',
                    options=[
                        {'label': 'By PMSA', 'value': 'pmsa_nm'},
                        {'label': 'By City', 'value': 'city_nm'},
                        {'label': 'By Volume Category', 'value': 'vcategory'},
                        {'label': 'By Road Class', 'value': 'rdClass'}
                    ],
                    value='rdClass',
                    clearable=False,
                    style={'width': '200px'}
                )
            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '5px'}),

            dcc.Graph(id='bar_fig', style={'height': '36%', 'marginBottom': '0px'}),
            html.H3("PRMSE", style={'marginTop': '5px'}),
            dcc.Graph(id='bar_fig2', style={'height': '30%', 'marginBottom': '0px'}),
            html.H3("Number of Observed Counts", style={'marginTop': '5px'}),
            dcc.Graph(id='count_fig', style={'height': '30%'})
        ], style={'flex': '1', 'padding': '5px', 'boxSizing': 'border-box','width':'33.3%','height': '100%'}),

       html.Div([
           html.H3("Model Day Flow VS Observed Daily Count"),
        html.Div([
            # Scatter plot container (takes ~70% of available height)
            dcc.Graph(
                id='scatter',
                figure=scatter_fig,
                style={'flex': '7', 'width': '100%', 'padding': '0', 'margin': '0'}
            ),
            # Lower container (ring + stats) takes ~30% of available height.
            html.Div([
                # Left: Ring Chart
                html.Div([
                    dcc.Graph(
                        id='source-ring',
                        figure=source_fig.update_layout(showlegend=False),
                        config={'displayModeBar': False},
                        style={'height': '100%', 'width': '100%', 'padding': '0', 'margin': '0'}
                    )
                ], style={'flex': '1', 'padding': '0', 'margin': '0'}),
                # Right: Stats
                html.Div(
                    id='stat-box',
                    children=[
                        html.Div([
                            html.H3(f"{slope_all:.2f}", style={'margin': '0', 'fontSize': '20px'}),
                            html.Small("Slope")
                        ], style={'textAlign': 'center', 'marginBottom': '10px'}),
                        html.Div([
                            html.H3(f"{r_squared_all:.2f}", style={'margin': '0', 'fontSize': '20px'}),
                            html.Small("R-Squared")
                        ], style={'textAlign': 'center', 'marginBottom': '10px'}),
                        html.Div([
                            html.H3(f"{prmse_all:.2f}", style={'margin': '0', 'fontSize': '20px'}),
                            html.Small("PRMSE")
                        ], style={'textAlign': 'center', 'marginBottom': '10px'}),
                        html.Div([
                            html.H3(f"{total_obs_all}", style={'margin': '0', 'fontSize': '20px'}),
                            html.Small("Total Observed Counts")
                        ], style={'textAlign': 'center'})
                    ],
                    style={
                        'flex': '1',
                        'padding': '0',
                        'margin': '0',
                        'display': 'flex',
                        'flexDirection': 'column',
                        'justifyContent': 'center'
                    }
                )
            ], style={
                'display': 'flex',
                'flexDirection': 'row',
                'flex': '3',
                'width': '100%',
                'padding': '0',
                'margin': '0'
            })
        ], style={
            'display': 'flex',
            'flexDirection': 'column',
            'height': '100%',
            'width': '100%',
            'padding': '0',
            'margin': '0'
        })
    ], style={'flex': '1', 'padding': '0', 'boxSizing': 'border-box', 'width': '33.3%', 'height': '100%'}),

        html.Div([
            html.H3("Map: Gap Day by Hwy Coverage ID"),
            leaflet_map
        ], style={'flex': '1', 'padding': '0px', 'boxSizing': 'border-box','height': '100%','width':'33.3%'})
    ], style={'display': 'flex', 'width': '100%', 'height': '700px'})


# === Define Page 2 Layout: Volume Validation by Hwy ===
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
                style={'overflowY': 'scroll', 'height': '600px'}  # Scroll if too many corridors
            )
        ], style={'width': '15%', 'padding': '10px', 'boxSizing': 'border-box'}),

        html.Div([
            html.H3("Line Chart: DAY_Flow vs count_day by Segment"),
            html.Div([
                dcc.Graph(id='line_plot', figure=line_fig, style={'height': '800px'})
            ], style={'overflowX': 'auto', 'width': '100%'})
        ], style={'width': '55%', 'padding': '10px', 'boxSizing': 'border-box'}),
        html.Div([
            html.H3("Map: Gap Day by Hwy Coverage ID"),
            leaflet_map
        ], style={'width': '30%', 'padding': '10px', 'boxSizing': 'border-box'})
    ], style={'display': 'flex', 'width': '100%', 'height': '800px'})

# === Define Page 3 Layout: VMT===
def page_vmt_comparison():
    from plotly.subplots import make_subplots

    def make_vmt_fig(group_col, title):
        df_vmt = df_filtered2.copy()

        # Group and rename
        grouped = df_vmt.groupby(group_col)[['DAY_Vmt', 'vmt_day']].sum().reset_index()
        grouped = grouped.rename(columns={group_col: 'Group'})

        # Melt in desired order: vmt_day (Observed) first
        melted = grouped.melt(
            id_vars='Group',
            value_vars=['vmt_day', 'DAY_Vmt'],
            var_name='Source',
            value_name='VMT'
        )

        # Map to display labels
        label_map = {'vmt_day': 'Observed VMT', 'DAY_Vmt': 'Model VMT'}
        color_map = {'Observed VMT': '#F65166', 'Model VMT': '#08306b'}
        melted['Source'] = melted['Source'].map(label_map)
        fig = px.bar(
            melted,
            x='Group',
            y='VMT',
            color='Source',
            barmode='group',
            labels={'VMT': 'VMT', 'Group': group_col},
            title=title,
            color_discrete_map=color_map
        )
        fig.update_layout(
            margin=dict(t=40, b=30, l=20, r=20),
            xaxis_title=None,
            yaxis_title=None,
            height=None 
        )
        
        return fig

    return html.Div([
        html.H2("VMT Comparison: Model vs Observed by Different Groups", style={'textAlign': 'center', 'marginBottom': '10px'}),

        html.Div([
            # Row 1
            html.Div([
                dcc.Graph(figure=make_vmt_fig('pmsa_nm', 'By PMSA'), style={'width': '50%', 'height': '100%'}),
                dcc.Graph(figure=make_vmt_fig('vcategory', 'By Category'), style={'width': '50%', 'height': '100%'})
            ], style={'display': 'flex', 'height': '50%'}),

            # Row 2
            html.Div([
                dcc.Graph(figure=make_vmt_fig('city_nm', 'By City'), style={'width': '50%', 'height': '100%'}),
                dcc.Graph(figure=make_vmt_fig('rdClass', 'By Road Class'), style={'width': '50%', 'height': '100%'})
            ], style={'display': 'flex', 'height': '50%'})
        ], style={'height': 'calc(100vh - 80px)'})  # Adjust to exclude H2 + padding
    ], style={'padding': '10px', 'height': '100vh', 'boxSizing': 'border-box',})



# === Full App Layout with Collapsible Sidebar ===
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),

html.Div([
    html.Button("☰ Menu", id="menu-button", n_clicks=0, style={
        'position': 'fixed',
        'top': '10px',
        'left': '10px',
        'zIndex': '1001'
    }),
    html.Div(id='sidebar-content', children=[
        html.H2(" "),
        html.Hr(),
        dcc.Link("Volume Validation", href="/", style={'display': 'block', 'margin': '10px'}),
        dcc.Link("Validation by Hwy", href="/volume_by_hwy", style={'display': 'block', 'margin': '10px'}),
        dcc.Link("VMT Comparison", href="/vmt_comparison", style={'display': 'block', 'margin': '10px'})
    ], style={
        'position': 'fixed',
        'top': '0',
        'left': '-200px',  # off-screen initially
        'width': '200px',
        'height': '100vh',
        'backgroundColor': '#f8f9fa',
        'padding': '20px',
        'boxSizing': 'border-box',
        'zIndex': '1000',
        'transition': 'left 0.3s'
    })
], id='sidebar-wrapper'),


    html.Div(id='page-content', style={'marginLeft': '0px','transition': 'margin-left 0.3s', 'padding': '20px','fontFamily': 'Open Sans, verdana, arial, sans-serif'})
])




# === Page Router Callback ===
@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def render_page(pathname):
    if pathname == '/volume_by_hwy':
        return page_volume_by_hwy()
    elif pathname == '/vmt_comparison':
        return page_vmt_comparison()
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

    return html.Div([
        html.B(f"Segment: {props.get('nm', 'N/A')}"),
        html.Br(),
        f"Hwy ID: {props.get('hwycovid', 'N/A')}",
        html.Br(),
        f"Length: {round(props.get('length', 0), 2)} meters",
        html.Br(),
        f"Gap Day: {props.get('gap_day', 'N/A')}%",
        html.Br(),
        f"Model Flow: {props.get('DAY_Flow', 'N/A')}",
        html.Br(),
        f"Observed Count: {props.get('count_day', 'N/A')}"
    ])

# === Map Highlight Callback ===
@app.callback(
    Output("geojson", "hideout"),
    Output("map", "center"),
    Output("map", "zoom"),
    Input("scatter", "clickData"),
    State("geojson", "hideout")
)
def zoom_from_scatter(clickData, hideout):
    if not clickData:
        return hideout, dash.no_update, dash.no_update

    selected_id = clickData["points"][0]["customdata"][0]
    return get_map_center(selected_id, hideout)

@app.callback(
    Output("geojson", "hideout", allow_duplicate=True),
    Output("map", "center", allow_duplicate=True),
    Output("map", "zoom", allow_duplicate=True),
    Input("line_plot", "clickData"),
    State("geojson", "hideout"),
    prevent_initial_call=True
)
def zoom_from_line(clickData, hideout):
    if not clickData:
        return hideout, dash.no_update, dash.no_update

    selected_id = clickData["points"][0]["customdata"][0]
    return get_map_center(selected_id, hideout)

def get_map_center(selected_id, hideout):
    hideout["highlight_id"] = selected_id
    for feature in geojson_data["features"]:
        if feature["properties"]["hwycovid"] == selected_id:
            coords = feature["geometry"]["coordinates"]
            mid_idx = len(coords) // 2
            center = coords[mid_idx][::-1]
            return hideout, center, 14
    return hideout, dash.no_update, dash.no_update

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
    State('bar_fig', 'figure'),
    prevent_initial_call=False
)

def update_all(click1, click2, click3, groupby_col, current_fig1):
    ctx = callback_context
    trigger = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

    # Get x-axis fixed order
    if current_fig1 and 'data' in current_fig1 and len(current_fig1['data']) > 0:
        x_axis_fixed = current_fig1['data'][0]['x']
    else:
        x_axis_fixed = None

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

    # Prepare data
    results = []
    count_results = []

    for group_val, group in df_filtered2.groupby(groupby_col):
        x = pd.to_numeric(group['count_day'], errors='coerce')
        y = pd.to_numeric(group['DAY_Flow'], errors='coerce')
        mask = ~np.isnan(x) & ~np.isnan(y)
        x_clean = x[mask]
        y_clean = y[mask]

        if len(x_clean) > 1:
            slope, intercept = np.polyfit(x_clean, y_clean, 1)
            y_pred = slope * x_clean + intercept
            r_squared = 1 - np.sum((y_clean - y_pred) ** 2) / np.sum((y_clean - y_clean.mean()) ** 2)
            rmse = np.sqrt(np.mean((y_clean - y_pred) ** 2))
            mean_obs = np.mean(y_clean)
            prmse = (rmse / mean_obs) * 100 if mean_obs != 0 else np.nan

            results.append({
                'Group': group_val,
                'R_squared': round(r_squared, 2),
                'Slope': round(slope, 2),
                'PRMSE': round(prmse, 2)
            })

        count_results.append({
            'Group': group_val,
            'Num_Observed': len(group)
        })

    result_df = pd.DataFrame(results)
    count_df = pd.DataFrame(count_results)

    if x_axis_fixed is None:
        x_axis_fixed = list(result_df['Group'])

    # === Bar 1: R² and Slope
    fig1 = go.Figure()

    # Build data separately
    opacity_val_r2 = 1
    opacity_val_slope = 1

    if selected_group:
        opacity_list_r2 = [1 if g == selected_group else 0.3 for g in result_df['Group']]
        opacity_list_slope = [1 if g == selected_group else 0.3 for g in result_df['Group']]
    else:
        opacity_list_r2 = [1 for _ in result_df['Group']]
        opacity_list_slope = [1 for _ in result_df['Group']]

    # Now add one trace for R_squared
    fig1.add_trace(go.Bar(
        x=result_df['Group'],
        y=result_df['R_squared'],
        name='R_squared',
        marker_color='#08306b',
        marker=dict(opacity=opacity_list_r2),  # control opacity INSIDE marker not at trace level
    ))

    # And one trace for Slope
    fig1.add_trace(go.Bar(
        x=result_df['Group'],
        y=result_df['Slope'],
        name='Slope',
        marker_color='#F65166',
        marker=dict(opacity=opacity_list_slope),
    ))

    fig1.update_layout(
        barmode='group',
        bargap=0.2,
        bargroupgap=0.05,
        xaxis=dict(tickangle=30, categoryorder='array', categoryarray=x_axis_fixed),
        yaxis_range=[0, 1.5],
        legend=dict(orientation='h', yanchor='bottom', y=1.1, xanchor='left', x=0),
        margin=dict(t=0, b=0, l=0, r=0),
    )

    # === Bar 2: PRMSE
    fig2 = go.Figure()

    for idx, row in result_df.iterrows():
        opacity_val = 1
        if selected_group:
            opacity_val = 1 if row['Group'] == selected_group else 0.3
        fig2.add_trace(go.Bar(
            x=[row['Group']],
            y=[row['PRMSE']],
            marker_color='#08306b',
            opacity=opacity_val,
            showlegend=False
        ))

    fig2.update_layout(
        barmode='group',
        xaxis=dict(tickangle=30, categoryorder='array', categoryarray=x_axis_fixed),
        yaxis_range=[0, result_df['PRMSE'].max() * 1.2],
        showlegend=False,
        margin=dict(t=0, b=0, l=0, r=0),
    )

    # === Bar 3: Number of Observed Counts
    fig3 = go.Figure()

    for idx, row in count_df.iterrows():
        opacity_val = 1
        if selected_group:
            opacity_val = 1 if row['Group'] == selected_group else 0.3
        fig3.add_trace(go.Bar(
            x=[row['Group']],
            y=[row['Num_Observed']],
            marker_color='#08306b',
            opacity=opacity_val,
            showlegend=False
        ))

    fig3.update_layout(
        barmode='group',
        xaxis=dict(tickangle=30, categoryorder='array', categoryarray=x_axis_fixed),
        yaxis_range=[0, count_df['Num_Observed'].max() * 1.2],
        showlegend=False,
        margin=dict(t=0, b=0, l=0, r=0),
    )

    # === Filtered data for stats and source
    if selected_group:
        sub_df = df_filtered2[df_filtered2[groupby_col] == selected_group]
    else:
        sub_df = df_filtered2

    x_all = pd.to_numeric(sub_df['count_day'], errors='coerce')
    y_all = pd.to_numeric(sub_df['DAY_Flow'], errors='coerce')
    mask_all = ~np.isnan(x_all) & ~np.isnan(y_all)
    x_clean_all = x_all[mask_all]
    y_clean_all = y_all[mask_all]

    slope_all, intercept_all = np.polyfit(x_clean_all, y_clean_all, 1)
    y_pred_all = slope_all * x_clean_all + intercept_all
    r_squared_all = 1 - np.sum((y_clean_all - y_pred_all) ** 2) / np.sum((y_clean_all - y_clean_all.mean()) ** 2)
    rmse_all = np.sqrt(np.mean((y_clean_all - y_pred_all) ** 2))
    mean_obs_all = np.mean(y_clean_all)
    prmse_all = (rmse_all / mean_obs_all) * 100 if mean_obs_all != 0 else np.nan
    total_obs_all = len(x_clean_all)

    source_color_map = {
        'PeMS': '#08306b',       # Moonshine
        'San Diego': '#F6C800',  # Sunshine
        'Chula Vista': '#F65166',# Confetti
        'Carlsbad': '#49C2D6',   # Splash
        'El Cajon': '#F2762E',   # Squash
        'Oceanside': '#2E87C8',    # Sky
        'Del Mar': '#A3E7D8',     # Mint
        'Coronado': '#C3B1E1'      # Lavender
    }

    # === Scatter plot ===
    # Fix scatter filtering
    if selected_group:
        scatter_df = df_filtered2[df_filtered2[groupby_col] == selected_group][['count_day', 'DAY_Flow', 'hwycovid']].dropna()
    else:
        scatter_df = df_filtered2[['count_day', 'DAY_Flow', 'hwycovid']].dropna()

     # Regression line
    x = scatter_df['count_day']
    y = scatter_df['DAY_Flow']
    slope, intercept = np.polyfit(x, y, 1)
    line_x = np.linspace(x.min(), x.max(), 100)
    line_y = slope * line_x + intercept
    r_squared = 1 - np.sum((y - (slope * x + intercept)) ** 2) / np.sum((y - y.mean()) ** 2)

    scatter_fig = go.Figure()

    # Add points first
    scatter_fig.add_trace(go.Scatter(
        x=scatter_df['count_day'],
        y=scatter_df['DAY_Flow'],
        mode='markers',
        name='Paired Data Point',
        marker=dict(size=7, color='#08306b', opacity=0.5),
        customdata=scatter_df[['hwycovid']]
    ))

    # Add regression line second
    scatter_fig.add_trace(go.Scatter(
        x=line_x,
        y=line_y,
        mode='lines',
        name='Best Fit Line',
        line=dict(color='#F65166', dash='dash', width=3)
    ))

    scatter_fig.update_layout(
    xaxis_title='Observed Count',
    yaxis_title='Model Flow',
    xaxis=dict(range=[-5000, 150000]), 
    yaxis=dict(range=[-5000, 150000]), 
    legend=dict(
        orientation='h',
        yanchor='bottom',
        y=1.02,
        xanchor='left',
        x=0
    ),
    margin=dict(t=20, b=0, l=40, r=20)
)
    
    # Build initial donut chart with fixed color mapping
    source_dist  = sub_df['source'].value_counts().reset_index()
    source_dist .columns = ['Source', 'Count']
    source_dist ['Percent'] = round(100 * source_dist ['Count'] / source_dist ['Count'].sum())

    # Apply color mapping
    colors = [source_color_map.get(src, '#CCCCCC') for src in source_dist ['Source']]

    source_fig = go.Figure(go.Pie(
        labels=source_dist['Source'],
        values=source_dist['Percent'],
        hole=0.6,
        textinfo='label+percent',
        marker=dict(colors=colors)
    ))
    source_fig.update_layout(margin=dict(t=0, b=20, l=20, r=0),showlegend=False)

    stat_box = html.Div([
    html.Div([
        html.H3(f"{slope_all:.2f}", style={'margin': '0', 'fontSize': '20px'}),
        html.Small("Slope")
    ], style={'textAlign': 'center', 'marginBottom': '30px'}),

    html.Div([
        html.H3(f"{r_squared_all:.2f}", style={'margin': '0', 'fontSize': '20px'}),
        html.Small("R-Squared")
    ], style={'textAlign': 'center', 'marginBottom': '30px'}),

    html.Div([
        html.H3(f"{prmse_all:.2f}", style={'margin': '0', 'fontSize': '20px'}),
        html.Small("PRMSE")
    ], style={'textAlign': 'center', 'marginBottom': '30px'}),

    html.Div([
        html.H3(f"{total_obs_all}", style={'margin': '0', 'fontSize': '20px'}),
        html.Small("Total Observed Counts")
    ], style={'textAlign': 'center', 'marginBottom': '20px'})
], style={'flex': '1', 'padding': '0px', 'display': 'flex', 'flexDirection': 'column', 'justifyContent': 'center'})


    return fig1, fig2, fig3, scatter_fig, source_fig, stat_box

@app.callback(
    Output('line_plot', 'figure'),
    Input('corridor_filter', 'value')
)
def update_line_chart(selected):
    all_corridors = sorted(df_filtered1['nm'].dropna().unique())

    if not selected:
        filtered_df = line_df.iloc[0:0]  # Return empty DataFrame
    elif 'ALL' in selected:
        filtered_df = line_df
    else:
        filtered_df = line_df[line_df['nm'].isin(selected)]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=filtered_df['hwycovid'],
        y=filtered_df['DAY_Flow'],
        customdata=filtered_df[['hwycovid']],
        mode='lines+markers',
        name='Model DAY_Flow',
        line=dict(color='#08306b')
    ))

    fig.add_trace(go.Scatter(
        x=filtered_df['hwycovid'],
        y=filtered_df['count_day'],
        customdata=filtered_df[['hwycovid']],
        mode='lines+markers',
        name='Observed count_day',
        line=dict(color='#F65166')
    ))

    fig.update_layout(
        xaxis_title='Highway Segment',
        yaxis_title='Volume',
        height=800,
        width=max(1000, len(filtered_df) * 30),  # Auto-scale width
        margin=dict(l=20, r=20, t=5, b=5),
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
            tickvals=filtered_df['hwycovid'],
            ticktext=filtered_df['Label'],
            tickfont=dict(size=10),
            showgrid=False,
            range=[-0.9, len(filtered_df) - 0.8]
        )
    )

    return fig

# === Run App ===
if __name__ == '__main__':
    app.run(debug=True, port=8050)
