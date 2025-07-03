import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dash import Dash, html, dash_table, dcc
import dash_leaflet as dl
from dash_extensions.javascript import assign


def build_scatter_plot(df, obs_col, model_col,id_column):
    """
    Create scatter plot with regression line for observed vs model volume.

    Parameters:
        df (pd.DataFrame): Filtered dataframe with relevant scenario.
        obs_col (str): Column name for observed values (e.g., 'count_day', 'truckaadt').
        model_col (str): Column name for modeled values (e.g., 'day_flow', 'truckflow').
        id_column: id column in df

    Returns:
        px.scatter: Plotly figure with points and best fit line.
        float: R-squared value.
        float: slope of regression line.
        float: prmse (as % of mean observed).
    """
    scatter_df = df[[obs_col, model_col, id_column]].dropna()
    # q_high = scatter_df[obs_col].quantile(0.99)
    # scatter_df = scatter_df[scatter_df[obs_col] <= q_high]
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
        custom_data=[id_column],
        labels={obs_col: 'Observed Count', model_col: 'Model Flow'},
        color_discrete_sequence=["#08306b"],
        opacity=0.3
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
    total_count = len(x_clean)

    if total_count == 1:
        x_val = x_clean.iloc[0]
        y_val = y_clean.iloc[0]

        slope = y_val / x_val if x_val != 0 else np.nan
        r_squared = np.nan
        prmse = ((y_val - x_val) / y_val) * 100 if y_val != 0 else np.nan

    elif total_count >= 2:
        slope, intercept = np.polyfit(x_clean, y_clean, 1)
        y_pred = slope * x_clean + intercept
        r_squared = 1 - np.sum((y_clean - y_pred) ** 2) / np.sum((y_clean - y_clean.mean()) ** 2)
        rmse = np.sqrt(np.mean((y_clean - y_pred) ** 2))
        prmse = (rmse / y_clean.mean()) * 100 if y_clean.mean() != 0 else np.nan
    
    else:
        slope, r_squared, prmse = np.nan, np.nan, np.nan

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
        'MTS':'#49C2D6',
        'Military': '#49C2D6',
        'El Cajon': '#F2762E',
        'Oceanside': '#2E87C8',
        'NCTD':'#2E87C8',
        'Port of San Diego': '#2E87C8', 
        'Del Mar': '#A3E7D8',
        'Caltrans':'#A3E7D8',
        'Coronado': '#C3B1E1'
    }

    source_dist = df[source_col].value_counts().reset_index()
    source_dist.columns = ['Source', 'Count']
    source_dist['Percent'] = round(100 * source_dist['Count'] / source_dist['Count'].sum())

    colors = [source_color_map.get(src, '#49C2D6') for src in source_dist['Source']]

    fig = go.Figure(go.Pie(
        labels=source_dist['Source'],
        values=source_dist['Percent'],
        hole=0.6,
        textinfo='label+percent',
        marker=dict(colors=colors)
    ))

    fig.update_layout(
        showlegend=False,
        margin=dict(t=5, b=5, l=5, r=5)
    )

    return fig


# === Create Leaflet Map ===
def create_map(initial_data=None, id_field="hwycovid"):
    if initial_data is None:
        initial_data = {"type": "FeatureCollection", "features": []}
    # Define a simple hover style
    hover_style = dict(weight=5, color='#666', dashArray='', fillOpacity=0.7)
    # === Define style function directly in JavaScript ===
    style_function = assign("""function(feature, context) {
        const hideout = context.hideout || {};
        const highlight_id = hideout.highlight_id;
        const id_field = hideout.id_field;

        const feature_id = feature.properties[id_field];
        const isHighlighted = highlight_id !== null && feature_id == highlight_id;

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
            };
        }

        return {
            color: color,
            weight: 2,
            opacity: 0.7
        };
    }""")
    return dl.Map(
        id='map',
        center=[32.9, -117],
        zoom=10, 
        children=[
            dl.TileLayer(
                url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
                attribution='© OpenStreetMap contributors, © CartoDB'
            ),
            dl.GeoJSON(
                data=initial_data,
                id="geojson",
                hoverStyle=hover_style,
                hideout={"highlight_id": None, "id_field": id_field, "selected": []},
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

def make_bar_figures(result_df, count_df, selected_group, x_axis_fixed=None):
    import plotly.graph_objects as go

    if x_axis_fixed is None:
        x_axis_fixed = list(result_df['Group'])

    # === Bar 1: R² + Slope
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(
        x=result_df['Group'],
        y=result_df['R_squared'],
        name='R²',
        marker_color='#08306b',
        marker=dict(opacity=[1 if g == selected_group or selected_group is None else 0.3 for g in result_df['Group']])
    ))
    fig1.add_trace(go.Bar(
        x=result_df['Group'],
        y=result_df['Slope'],
        name='Slope',
        marker_color='#F65166',
        marker=dict(opacity=[1 if g == selected_group or selected_group is None else 0.3 for g in result_df['Group']])
    ))
    fig1.update_layout(
        barmode='group',
        xaxis=dict(tickangle=30, categoryorder='array', categoryarray=x_axis_fixed),
        margin=dict(t=0, b=0, l=0, r=0),
        showlegend=False
    )

    # === Bar 2: PRMSE
    fig2 = go.Figure()
    for _, row in result_df.iterrows():
        fig2.add_trace(go.Bar(
            x=[row['Group']],
            y=[row['PRMSE']],
            marker_color='#08306b',
            opacity=1 if row['Group'] == selected_group or selected_group is None else 0.3,
            showlegend=False
        ))
    fig2.update_layout(
        xaxis=dict(tickangle=30, categoryorder='array', categoryarray=x_axis_fixed),
        margin=dict(t=0, b=0, l=0, r=0),
        showlegend=False
    )

    # === Bar 3: Count
    fig3 = go.Figure()
    for _, row in count_df.iterrows():
        fig3.add_trace(go.Bar(
            x=[row['Group']],
            y=[row['Num_Observed']],
            marker_color='#08306b',
            opacity=1 if row['Group'] == selected_group or selected_group is None else 0.3,
            showlegend=False
        ))
    fig3.update_layout(
        xaxis=dict(tickangle=30, categoryorder='array', categoryarray=x_axis_fixed),
        margin=dict(t=0, b=0, l=0, r=0),
        showlegend=False
    )

    return fig1, fig2, fig3

def bar_scatter_layout(
    bar_id, bar2_id, count_id,
    scatter_id, ring_id, stat_id,
    slope_all, r_squared_all, prmse_all, total_obs_all,
    show_groupby_selector=True
):
    selector_div = html.Div([
        html.H3("R² and Slope", style={'marginRight': '20px'}),
    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '5px'}) if not show_groupby_selector else html.Div([
        html.H3("R² and Slope", style={'marginRight': '20px'}),
        dcc.Dropdown(
            id='groupby_selector',
            options=[
                {'label': 'By PMSA', 'value': 'pmsa_nm'},
                {'label': 'By City', 'value': 'city_nm'},
                {'label': 'By Volume Category', 'value': 'vcategory'},
                {'label': 'By Road Class', 'value': 'rdclass'}
            ],
            value='rdclass',
            clearable=False,
            style={'width': '200px'}
        )
    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '5px'})

    # LEFT COLUMN — bar charts
    left_column = html.Div([
        selector_div,
        dcc.Graph(id=bar_id, style={'height': '36%', 'marginBottom': '0px'}),
        html.H3("PRMSE", style={'marginTop': '5px'}),
        dcc.Graph(id=bar2_id, style={'height': '30%', 'marginBottom': '0px'}),
        html.H3("Number of Observed Counts", style={'marginTop': '5px'}),
        dcc.Graph(id=count_id, style={'height': '30%'})
    ], style={'flex': '1', 'padding': '5px', 'boxSizing': 'border-box', 'width': '33.3%', 'height': '100%'})

    # MIDDLE COLUMN — scatter, ring, stats
    middle_column = html.Div([
        html.H3("Model Day Flow VS Observed Daily Count"),
        dcc.Graph(id=scatter_id, style={'flex': '7', 'width': '100%', 'padding': '0', 'margin': '0'}),

        html.Div([
            html.Div([
                dcc.Graph(id=ring_id, config={'displayModeBar': False},
                          style={'height': '300px', 'width': '300px'})
            ], style={'flex': '1', 'display': 'flex', 'padding': '0', 'margin': '0',
                      'justifyContent': 'center', 'alignItems': 'center'}),

            html.Div(id=stat_id, children=[
                html.Div([html.H3(f"{slope_all:.2f}", style={'margin': '0', 'fontSize': '20px'}), html.Small("Slope")],
                         style={'textAlign': 'center', 'marginBottom': '10px'}),
                html.Div([html.H3(f"{r_squared_all:.2f}", style={'margin': '0', 'fontSize': '20px'}), html.Small("R²")],
                         style={'textAlign': 'center', 'marginBottom': '10px'}),
                html.Div([html.H3(f"{prmse_all:.2f}", style={'margin': '0', 'fontSize': '20px'}), html.Small("PRMSE")],
                         style={'textAlign': 'center', 'marginBottom': '10px'}),
                html.Div([html.H3(f"{total_obs_all}", style={'margin': '0', 'fontSize': '20px'}), html.Small("Count")],
                         style={'textAlign': 'center'})
            ], style={
                'flex': '1',
                'padding': '0',
                'display': 'flex',
                'flexDirection': 'column',
                'justifyContent': 'center'
            })
        ], style={'display': 'flex', 'flexDirection': 'row', 'flex': '3', 'width': '100%',
                  'padding': '0', 'margin': '0'})
    ], style={'flex': '1', 'padding': '0', 'boxSizing': 'border-box', 'width': '33.3%', 'height': '100%'})

    return left_column, middle_column

def prepare_boarding_tables(df):
    time_periods = ['ea', 'am', 'md', 'pm', 'ev', 'day']
    mode_col = 'mode_name'

    # Observed
    observed = df.groupby(mode_col)[[f'board_{tp}' for tp in time_periods]].sum().round(0)

    # Model
    model = df.groupby(mode_col)[[f'{tp}_board' for tp in time_periods]].sum().round(0)
    model.columns = [f'board_{tp}' for tp in time_periods]

    # Difference
    diff = model - observed
    diff = diff.round(0)

    # Gap (%)
    gap = ((model - observed) / observed.replace(0, np.nan) * 100).round(0).astype('Int64')

    # Add totals
    observed.loc['Total'] = observed.sum()
    model.loc['Total'] = model.sum()
    diff.loc['Total'] = diff.sum()

    # Calculate total gap from raw df, not groupby
    total_gap_dict = {}
    for tp in time_periods:
        obs_sum = df[f'board_{tp}'].sum()
        model_sum = df[f'{tp}_board'].sum()
        gap_pct = ((model_sum - obs_sum) / obs_sum * 100) if obs_sum != 0 else np.nan
        total_gap_dict[f'board_{tp}'] = round(gap_pct)

    gap.loc['Total'] = pd.Series(total_gap_dict).astype('Int64')

    return observed, model, diff, gap