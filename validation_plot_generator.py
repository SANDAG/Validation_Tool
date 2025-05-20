import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dash import Dash, html, dash_table, dcc
import dash_leaflet as dl
from dash_extensions.javascript import assign

source_color_map = {
    'PeMS': '#08306b',
    'San Diego': '#F6C800',
    'Chula Vista': '#F65166',
    'Carlsbad': '#49C2D6',
    'El Cajon': '#F2762E',
    'Oceanside': '#2E87C8',
    'Del Mar': '#A3E7D8',
    'Coronado': '#C3B1E1'
}

def build_scatter_plot(df, obs_col, model_col):
    """
    Create scatter plot with regression line for observed vs model volume.

    Parameters:
        df (pd.DataFrame): Filtered dataframe with relevant scenario.
        obs_col (str): Column name for observed values (e.g., 'count_day', 'truckaadt').
        model_col (str): Column name for modeled values (e.g., 'day_flow', 'truckflow').

    Returns:
        go.Figure: Plotly figure with points and best fit line.
        float: R-squared value.
        float: slope of regression line.
        float: prmse (as % of mean observed).
    """
    scatter_df = df[[obs_col, model_col, 'hwycovid']].dropna()
    x = scatter_df[obs_col]
    y = scatter_df[model_col]
    
    # Fit regression line
    slope, intercept = np.polyfit(x, y, 1)
    line_x = np.linspace(x.min(), x.max(), 100)
    line_y = slope * line_x + intercept
    r_squared = 1 - np.sum((y - (slope * x + intercept))**2) / np.sum((y - y.mean())**2)
    
    # PRMSE calculation
    rmse = np.sqrt(np.mean((y - (slope * x + intercept))**2))
    prmse = (rmse / y.mean()) * 100 if y.mean() != 0 else np.nan

    # Plot
    fig = px.scatter(
        scatter_df,
        x=obs_col,
        y=model_col,
        custom_data=['hwycovid'],
        labels={obs_col: 'Observed Count', model_col: 'Model Flow'},
        color_discrete_sequence=["#08306b"],
        opacity=0.5
    )
    fig.update_traces(marker=dict(size=9))
    fig.add_trace(go.Scatter(
        x=line_x,
        y=line_y,
        mode='lines',
        name='Best Fit Line',
        line=dict(color='#F65166', dash='dash', width=3)
    ))
    fig.update_layout(
        xaxis_title='Observed Volume',
        yaxis_title='Model Volume',
        margin=dict(t=20, b=0, l=40, r=20),
        showlegend=False
    )

    return fig, r_squared, slope, prmse

def compute_overall_stats(df, obs_col, model_col):
    """
    Compute overall slope, R², PRMSE, and count of observed-model pairs.

    Parameters:
        df (pd.DataFrame): Filtered dataframe.
        obs_col (str): Column name for observed values (e.g., 'count_day', 'truckaadt').
        model_col (str): Column name for model values (e.g., 'day_flow', 'truckflow').

    Returns:
        tuple: (slope, r_squared, prmse, total_count)
    """
    x_all = pd.to_numeric(df[obs_col], errors='coerce')
    y_all = pd.to_numeric(df[model_col], errors='coerce')
    mask_all = ~np.isnan(x_all) & ~np.isnan(y_all)
    x_clean = x_all[mask_all]
    y_clean = y_all[mask_all]

    if len(x_clean) < 2:
        return np.nan, np.nan, np.nan, 0

    slope, intercept = np.polyfit(x_clean, y_clean, 1)
    y_pred = slope * x_clean + intercept
    r_squared = 1 - np.sum((y_clean - y_pred)**2) / np.sum((y_clean - y_clean.mean())**2)
    rmse = np.sqrt(np.mean((y_clean - y_pred)**2))
    prmse = (rmse / y_clean.mean()) * 100 if y_clean.mean() != 0 else np.nan
    total_count = len(x_clean)

    return slope, r_squared, prmse, total_count

def build_source_ring_chart(df, source_col='source'):
    """
    Create a ring (donut) chart showing the percentage distribution of sources.

    Parameters:
        df (pd.DataFrame): DataFrame with a column for source types.
        source_col (str): Column name containing the source categories.

    Returns:
        go.Figure: A Plotly donut chart figure.
    """
    source_color_map = {
        'PeMS': '#08306b',
        'San Diego': '#F6C800',
        'Chula Vista': '#F65166',
        'Carlsbad': '#49C2D6',
        'El Cajon': '#F2762E',
        'Oceanside': '#2E87C8',
        'Del Mar': '#A3E7D8',
        'Coronado': '#C3B1E1'
    }

    source_dist = df[source_col].value_counts().reset_index()
    source_dist.columns = ['Source', 'Count']
    source_dist['Percent'] = round(100 * source_dist['Count'] / source_dist['Count'].sum())

    colors = [source_color_map.get(src, '#CCCCCC') for src in source_dist['Source']]

    fig = go.Figure(go.Pie(
        labels=source_dist['Source'],
        values=source_dist['Percent'],
        hole=0.6,
        textinfo='label+percent',
        marker=dict(colors=colors)
    ))

    fig.update_layout(
        showlegend=False,
        legend=dict(orientation="v", x=1.2, y=0.5),
        margin=dict(t=5, b=5, l=5, r=5)
    )

    return fig

# Define a simple hover style
hover_style = dict(weight=5, color='#666', dashArray='', fillOpacity=0.7)
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
            weight: 7,
            opacity: 1.0
        };
    }

    return {
        color: color,
        weight: 2,
        opacity: 0.8
    };
}""")
# === Create Leaflet Map ===
def create_map(geojson_data):
    return dl.Map(
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

def make_vmt_fig(df_vmt, group_col, title):

    # Group and rename
    grouped = df_vmt.groupby(group_col)[['day_vmt', 'vmt_day']].sum().reset_index()
    grouped = grouped.rename(columns={group_col: 'Group'})

    # Melt in desired order: vmt_day (Observed) first
    melted = grouped.melt(
        id_vars='Group',
        value_vars=['vmt_day', 'day_vmt'],
        var_name='Source',
        value_name='VMT'
    )

    # Map to display labels
    label_map = {'vmt_day': 'Observed VMT', 'day_vmt': 'Model VMT'}
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


