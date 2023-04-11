from dash import Input, Output, Dash, html, dcc, dash_table
import plotly.express as px
import pandas as pd
from pathlib import Path
import json

# PARAMS
DATA_PATH = Path("./data")
SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "20rem",
    "padding": "2rem 1rem",
    "background-color": "#018184"
}
CONTENT_STYLE = {
    "margin-left": "22rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem"
}
DROPDOWN_DICT = {
    "Overall Attendance By Year": ["Year"],
    "Attendance By Year And District": ["Year", "District"],
    "Attendance By Year And Gender": ["Year", "Gender"],
    "Attendance By Year And Cohort": ["Year", "Age Group"]
}
DISTR_TO_KEEP = [
    "Agago",
    "Amuru",
    "Gulu",
    "Gulu City",
    "Kitgum",
    "Nwoya",
    "Omoro",
    "Zombo"
]
######

# -------------------------------------------------------------------------------
# Import and clean data

with open(str((DATA_PATH / "geo_subc.json").resolve())) as f:
    df_geo_subc = json.load(f)

with open(str((DATA_PATH / "geo_distr.json").resolve())) as f:
    df_geo_distr = json.load(f)

df_attend = (
    pd.read_csv(DATA_PATH / "All_Data_Voice_DGF.csv")
    .assign(
        Date=lambda x: pd.to_datetime(x["Date"]),
        Year=lambda x: x["Date"].dt.year,
        Age_Group=lambda x: pd.cut(
            x["Age"],
            right=False,
            bins=[0, 20, 30, 40, 50, 60, x["Age"].max()],
            labels=["Under 20", "20s", "30s", "40s", "50s", "Over 60"]
        )
    )
    .dropna(subset="Year")
    .rename(
        columns={"Age_Group": "Age Group"}
    )
    
)

df_single = (
    df_attend
    .drop_duplicates(subset="Personal_Id", keep="first")
    .assign(Year=lambda x: x["Year"].astype(int))
)

df_repeated = (
    df_attend
    .groupby("Personal_Id", as_index=False)
    .agg(
        Attendances= ("Personal_Id", "count"),
        First_Name=("First_Name", "first"),
        Last_Name=("Last_Name", "first"),
        District=("District", "first"),
        Subcounty=("Subcounty", "first")
    )
    .sort_values(by="Attendances", ascending=False)
    .rename(
        columns={
            "First_Name": "First Name",
            "Last_Name": "Last Name"
        }
    )
    .query("Attendances > 1")
)

# ---------------------------------
# Initialize app
app = Dash(
    __name__,
    # external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[
        {
            "name": "viewport", 
            "content": "width=device-width, initial-scale=1"
        }
    ],
)
server = app.server

# ------------------------------------
# Components
sidebar = html.Div(
    children=[
        html.H2(
            "GWED-G\n Monitoring Tool",
            className="display-6",
            style={"color": "white", "fontWeight": "bold"}
        ),
        html.Hr(style={'borderWidth': "1vh", "width": "100%", "borderColor": "white","opacity": "unset"}),
        html.P(
            "Choose the geography level and year to map",
            className="lead",
            style={"color": "white"}
        ),
        dcc.Dropdown(
            options=[
                "District",
                "Subcounty",
            ],
            value="Subcounty",
            multi=False,
            id="geography_dropdown"
        ),
        dcc.Dropdown(
            options=df_attend["Year"].unique(),
            value=df_attend["Year"].max(),
            multi=False,
            id="year_dropdown"
        ),
        html.Hr(style={"color": "white", "weight": 4}),
        html.P(
            "Choose the indicator to display",
            className="lead",
            style={"color": "white"}
        ),
        dcc.Dropdown(
            options=[
                "Overall Attendance By Year",
                "Attendance By Year And District",
                "Attendance By Year And Gender",
                "Attendance By Year And Cohort"
            ],
            value="Overall Attendance By Year",
            multi=False,
            id="dropdown"
        ),
    ],
    style=SIDEBAR_STYLE
)

content = html.Div(
    children=[
        html.H3(
            children="Attendance Map",
            style={"textAlign": "center"}
        ),
        dcc.Graph(id="map"),
        html.H3(
            children="Attendees Over Time",
            style={"textAlign": "center"}
        ),
        dcc.Graph(id="plot"),
        html.Hr(style={'borderWidth': "2vh", "width": "100%", "borderColor": "#018184","opacity": "unset"}),
        html.H3(
            children="Top Attendees",
            style={"textAlign": "center"}
        ),
        dash_table.DataTable(
            data=df_repeated.to_dict("records"),
            columns=[
                {"name": "First Name", "id": "First Name", "type": "text", "filter_options": {"case": "insensitive"}},
                {"name": "Last Name", "id": "Last Name", "type": "text", "filter_options": {"case": "insensitive"}},
                {"name": "District", "id": "District", "type": "text", "filter_options": {"case": "insensitive"}},
                {"name": "Subcounty", "id": "Subcounty", "type": "text", "filter_options": {"case": "insensitive"}},
                {"name": "Attendances", "id": "Attendances", "type": "numeric",}
            ],
            style_cell={
                'padding-right': '5px',
                'padding-left': '5px',
                'marginLeft': 'auto',
                'marginRight': 'auto'
            },
            filter_action="native",
            sort_action="native",
            sort_mode="multi",
            page_action="native",
            page_current= 0,
            page_size=10,
        )
    ],
    id="main-body", 
    style=CONTENT_STYLE
)


#--------------------------------------------------------------
# App layout

app.layout = html.Div(
    children=[
        sidebar,
        content,
    ])

# --------------------------------------------------------
# Callbacks

@app.callback(
    [
        Output(component_id="map", component_property="figure"),
        Output(component_id="plot", component_property="figure"),
    ],
    [
        Input(component_id="geography_dropdown", component_property="value"),
        Input(component_id="year_dropdown", component_property="value"),
        Input(component_id="dropdown", component_property="value"),
    ]
)
def update_graph(geo_level, year, indicator):
        
    if geo_level == "Subcounty":
        df_map = df_geo_subc.copy()
    else:
        df_map = df_geo_distr.copy()

    df_data = (
        df_attend
        .query(f"Year == {year}")
        .dropna(subset="Year")
        .groupby(geo_level, as_index=False)
        .agg(
            Attendances=("Personal_Id", len)
        )
    )
    geo_fig = px.choropleth_mapbox(
        data_frame=df_data,
        geojson=df_map,
        locations=geo_level,
        featureidkey=f"properties.{geo_level}",
        color="Attendances",
        hover_data=[geo_level, "Attendances"],
        mapbox_style="carto-positron",
        center={"lat": 2.9, "lon": 32.1},
        zoom=7.2,
        opacity=0.7,
        color_continuous_scale=px.colors.sequential.YlOrRd,
    )


    df = (
        df_single
        .copy()
        .groupby(DROPDOWN_DICT[indicator], as_index=False)
        .agg(Participants=("Personal_Id", "count"))
    )

    if DROPDOWN_DICT[indicator] == ["Year"]:
        fig = px.bar(
            df,
            x="Year",
            y="Participants"
        )
    else:
        fig = px.bar(
            df,
            x="Year",
            y="Participants",
            color=DROPDOWN_DICT[indicator][1],
            barmode="group"
        )
    fig.update_layout(
        xaxis=dict(
            tickvals=df["Year"].unique(),
            tickmode="array",
        )
    )
    return geo_fig, fig


if __name__ == '__main__':
    app.run_server(host="0.0.0.0", port=80, debug=False)

